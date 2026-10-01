import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";
import type { Device, Room, Vec3 } from "./api";

const DEFAULT_ROOM: Room = { name: "Room", size: [5, 2.6, 4], furniture: [] };
// LED bytes are scaled past 1.0 so bright pixels cross the bloom threshold
const LED_GAIN = 3;
// Room light at level 1, enough to see the room clearly with the strips off
const ROOM_LIGHT_MAX = 3;
// Strips light the room through rectangular area lights laid along them, one per
// stretch of strip. Area lights give a soft wash instead of point-light hot spots
const MAX_WASH_LIGHTS = 24;
const WASH_STRETCH = 0.8; // metres of strip per light
const WASH_HEIGHT = 0.08; // metres, roughly the glow width of a strip
const WASH_GAIN = 60;
// Lights float this far off the wall, toward the middle of the room
const WASH_OFFSET = 0.04;

interface Wash {
  light: THREE.RectAreaLight;
  from: number;
  to: number;
}

interface Strip {
  count: number;
  mesh: THREE.InstancedMesh;
  washes: Wash[];
}

RectAreaLightUniformsLib.init();

/** Places `count` points evenly along a polyline by arc length */
function pointsAlong(path: Vec3[], count: number): THREE.Vector3[] {
  const vertices = path.map((p) => new THREE.Vector3(...p));
  const lengths = vertices.slice(1).map((v, i) => v.distanceTo(vertices[i]));
  const total = lengths.reduce((a, b) => a + b, 0);
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < count; i++) {
    let distance = ((i + 0.5) / count) * total;
    let segment = 0;
    while (segment < lengths.length - 1 && distance > lengths[segment]) distance -= lengths[segment++];
    const t = lengths[segment] ? distance / lengths[segment] : 0;
    points.push(vertices[segment].clone().lerp(vertices[segment + 1], t));
  }
  return points;
}

/** Normal pointing into the room from the wall, floor or ceiling closest to `point` */
function mountingNormal(point: THREE.Vector3, [w, h, d]: Vec3): THREE.Vector3 {
  const surfaces: [number, THREE.Vector3][] = [
    [point.x, new THREE.Vector3(1, 0, 0)],
    [w - point.x, new THREE.Vector3(-1, 0, 0)],
    [point.y, new THREE.Vector3(0, 1, 0)],
    [h - point.y, new THREE.Vector3(0, -1, 0)],
    [point.z, new THREE.Vector3(0, 0, 1)],
    [d - point.z, new THREE.Vector3(0, 0, -1)],
  ];
  return surfaces.reduce((closest, surface) => (surface[0] < closest[0] ? surface : closest))[1];
}

/** Strips without a layout get stacked along the back wall */
function fallbackPath(index: number, room: Room): Vec3[] {
  const [w, h] = room.size;
  const y = Math.max(0.2, h - 0.3 - index * 0.35);
  return [[0.2, y, 0.03], [w - 0.2, y, 0.03]];
}

export class RoomView {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(50, 1, 0.05, 100);
  private controls: OrbitControls;
  private composer: EffectComposer;
  private bloom: UnrealBloomPass;
  private roomGroup = new THREE.Group();
  private walls: { mesh: THREE.Mesh; hideWhen: (camera: THREE.Vector3) => boolean }[] = [];
  private strips = new Map<string, Strip>();
  private layoutKey = "";
  private color = new THREE.Color();
  private roomLight = new THREE.HemisphereLight("#dfe4ee", "#4a4440", 0);
  private ledBrightness = 1;

  private resizeObserver: ResizeObserver;

  constructor(private container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    container.appendChild(this.renderer.domElement);

    this.scene.background = new THREE.Color("#08090b");
    this.scene.add(this.roomLight);
    this.scene.add(this.roomGroup);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.maxPolarAngle = Math.PI * 0.49;
    this.controls.minDistance = 1;
    this.controls.maxDistance = 20;

    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    // Ambient occlusion darkens corners and contact points so the room has depth
    const ambientOcclusion = new GTAOPass(this.scene, this.camera);
    ambientOcclusion.updateGtaoMaterial({ radius: 0.6, distanceExponent: 1.5, scale: 1.2 });
    this.composer.addPass(ambientOcclusion);
    this.bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.85, 0.45, 0.9);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    this.resize();
    this.renderer.setAnimationLoop(() => this.render());
  }

  dispose() {
    this.renderer.setAnimationLoop(null);
    this.resizeObserver.disconnect();
    this.controls.dispose();
    this.composer.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  /** General room lighting from 0 (dark, only the strips glow) to 1 */
  setRoomLight(level: number) {
    this.roomLight.intensity = level * ROOM_LIGHT_MAX;
  }

  /** How bright the LEDs look and how much they light the room. View only, 1 is normal */
  setLedBrightness(level: number) {
    this.ledBrightness = level;
    for (const strip of this.strips.values()) {
      for (const { light } of strip.washes) light.intensity = WASH_GAIN * level;
    }
  }

  /** Rebuilds the scene when the room or the strips change */
  setLayout(room: Room | null, devices: Device[]) {
    room = room ?? DEFAULT_ROOM;
    const key = JSON.stringify([room, devices.map((d) => [d.name, d.leds, d.layout])]);
    if (key === this.layoutKey) return;
    const firstBuild = this.layoutKey === "";
    this.layoutKey = key;

    this.roomGroup.clear();
    this.walls = [];
    this.strips.clear();
    const [w, h, d] = room.size;
    this.roomGroup.position.set(-w / 2, 0, -d / 2);

    this.buildShell(w, h, d);
    for (const item of room.furniture) this.buildFurniture(item);

    const totalLeds = devices.reduce((sum, d) => sum + d.leds, 0) || 1;
    devices.forEach((device, i) => {
      // Share the light budget by strip length so many strips can't blow it
      const budget = Math.max(1, Math.floor((MAX_WASH_LIGHTS * device.leds) / totalLeds));
      this.buildStrip(device, device.layout ?? fallbackPath(i, room), budget, room.size);
    });

    if (firstBuild) {
      this.camera.position.set(w * 0.35, h * 1.35, d * 1.25);
      this.controls.target.set(0, h * 0.4, 0);
    }
  }

  setFrame(leds: Record<string, Uint8Array>) {
    for (const [name, bytes] of Object.entries(leds)) {
      const strip = this.strips.get(name);
      if (!strip) continue;
      const count = Math.min(strip.count, Math.floor(bytes.length / 3));
      const gain = (LED_GAIN * this.ledBrightness) / 255;
      for (let i = 0; i < count; i++) {
        this.color.setRGB(bytes[i * 3] * gain, bytes[i * 3 + 1] * gain, bytes[i * 3 + 2] * gain);
        strip.mesh.setColorAt(i, this.color);
      }
      // LEDs past the end of a short packet stay dark, like on the real strip
      this.color.setRGB(0, 0, 0);
      for (let i = count; i < strip.count; i++) strip.mesh.setColorAt(i, this.color);
      if (strip.mesh.instanceColor) strip.mesh.instanceColor.needsUpdate = true;

      for (const { light, from, to } of strip.washes) {
        let r = 0, g = 0, b = 0;
        const end = Math.min(to, count);
        for (let i = from; i < end; i++) {
          r += bytes[i * 3]; g += bytes[i * 3 + 1]; b += bytes[i * 3 + 2];
        }
        const n = Math.max(1, to - from) * 255;
        light.color.setRGB(r / n, g / n, b / n);
      }
    }
  }

  private buildShell(w: number, h: number, d: number) {
    // Light, matte surfaces so the strips' light shows up on them
    const wallMaterial = () => new THREE.MeshStandardMaterial({ color: "#b9b6b0", roughness: 0.95 });
    const floorMaterial = new THREE.MeshStandardMaterial({ color: "#6e655c", roughness: 0.85 });
    const plane = (width: number, height: number, material: THREE.Material) =>
      new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);

    const floor = plane(w, d, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(w / 2, 0, d / 2);
    this.roomGroup.add(floor);

    // Walls the camera is behind get hidden so the room reads like a dollhouse
    const back = plane(w, h, wallMaterial());
    back.position.set(w / 2, h / 2, 0);
    const front = plane(w, h, wallMaterial());
    front.rotation.y = Math.PI;
    front.position.set(w / 2, h / 2, d);
    const left = plane(d, h, wallMaterial());
    left.rotation.y = Math.PI / 2;
    left.position.set(0, h / 2, d / 2);
    const right = plane(d, h, wallMaterial());
    right.rotation.y = -Math.PI / 2;
    right.position.set(w, h / 2, d / 2);
    const ceiling = plane(w, d, wallMaterial());
    ceiling.rotation.x = Math.PI / 2;
    ceiling.position.set(w / 2, h, d / 2);

    const local = (c: THREE.Vector3) => c.clone().sub(this.roomGroup.position);
    this.walls = [
      { mesh: back, hideWhen: (c) => local(c).z < 0 },
      { mesh: front, hideWhen: (c) => local(c).z > d },
      { mesh: left, hideWhen: (c) => local(c).x < 0 },
      { mesh: right, hideWhen: (c) => local(c).x > w },
      { mesh: ceiling, hideWhen: (c) => local(c).y > h },
    ];
    for (const { mesh } of this.walls) this.roomGroup.add(mesh);
  }

  private buildFurniture(item: Room["furniture"][number]) {
    const material =
      item.kind === "screen"
        ? new THREE.MeshStandardMaterial({ color: item.color, roughness: 0.15, metalness: 0.4 })
        : item.kind === "window"
          ? new THREE.MeshStandardMaterial({ color: item.color, emissive: "#1b2c44", emissiveIntensity: 0.35, roughness: 0.35 })
          : new THREE.MeshStandardMaterial({ color: item.color, roughness: 0.8 });
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(...item.size), material);
    mesh.position.set(item.pos[0] + item.size[0] / 2, item.pos[1] + item.size[1] / 2, item.pos[2] + item.size[2] / 2);
    this.roomGroup.add(mesh);
  }

  private buildStrip(device: Device, path: Vec3[], lightBudget: number, roomSize: Vec3) {
    const points = pointsAlong(path, device.leds);
    const geometry = new THREE.SphereGeometry(0.016, 8, 6);
    const material = new THREE.MeshBasicMaterial({ toneMapped: false });
    const mesh = new THREE.InstancedMesh(geometry, material, device.leds);
    const matrix = new THREE.Matrix4();
    points.forEach((p, i) => {
      mesh.setMatrixAt(i, matrix.makeTranslation(p.x, p.y, p.z));
      mesh.setColorAt(i, new THREE.Color(0, 0, 0));
    });
    this.roomGroup.add(mesh);
    const washes = this.buildWashes(points, lightBudget, roomSize);
    this.strips.set(device.name, { count: device.leds, mesh, washes });
  }

  /**
   * Area lights along a strip, each covering an equal run of LEDs.
   *
   * An area light only lights what is in front of its plane, so each one faces
   * straight out from the surface its strip is mounted on. Tilted lights would
   * cut a hard line where their plane crosses the neighbouring walls.
   */
  private buildWashes(points: THREE.Vector3[], lightBudget: number, roomSize: Vec3): Wash[] {
    let length = 0;
    for (let i = 1; i < points.length; i++) length += points[i].distanceTo(points[i - 1]);
    const count = Math.min(lightBudget, Math.max(1, Math.round(length / WASH_STRETCH)));

    const washes: Wash[] = [];
    for (let i = 0; i < count; i++) {
      const from = Math.floor((i * points.length) / count);
      const to = Math.floor(((i + 1) * points.length) / count);
      const start = points[from];
      const end = points[Math.max(from, to - 1)];
      const middle = start.clone().lerp(end, 0.5);
      const along = end.clone().sub(start);
      const width = Math.max(along.length(), 0.05);
      if (along.lengthSq() === 0) along.set(1, 0, 0);
      along.normalize();

      const facing = mountingNormal(middle, roomSize);
      // Keep the strip direction in the light's plane
      along.sub(facing.clone().multiplyScalar(along.dot(facing)));
      if (along.lengthSq() < 1e-6) along.set(facing.y === 0 ? 0 : 1, facing.y === 0 ? 1 : 0, 0);
      along.normalize();

      // Lights shine down their -Z axis, so Z points back at the wall
      const back = facing.clone().negate();
      const up = new THREE.Vector3().crossVectors(back, along);
      const light = new THREE.RectAreaLight("#000000", WASH_GAIN * this.ledBrightness, width, WASH_HEIGHT);
      light.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(along, up, back));
      light.position.copy(middle).addScaledVector(facing, WASH_OFFSET);
      this.roomGroup.add(light);
      washes.push({ light, from, to });
    }
    return washes;
  }

  private resize() {
    const { clientWidth: width, clientHeight: height } = this.container;
    if (!width || !height) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
    this.composer.setSize(width, height);
    this.bloom.resolution.set(width, height);
  }

  private render() {
    this.controls.update();
    for (const wall of this.walls) wall.mesh.visible = !wall.hideWhen(this.camera.position);
    this.composer.render();
  }
}
