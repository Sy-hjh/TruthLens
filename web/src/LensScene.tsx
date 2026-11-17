import { useEffect, useRef, useState } from "react";
import { Icon } from "./ui";
export default function LensScene({ motion }: { motion: boolean }) {
  const host = useRef<HTMLDivElement>(null),
    expanded = useRef(false);
  const motionState = useRef(motion);
  useEffect(() => {
    motionState.current = motion;
  }, [motion]);
  const [open, setOpen] = useState(false),
    [ready, setReady] = useState(false),
    [revealed, setRevealed] = useState(false);
  useEffect(() => {
    let disposed = false,
      cleanup = () => {};
    void import("three").then((T) => {
      if (disposed || !host.current) return;
      const el = host.current;
      let renderer: InstanceType<typeof T.WebGLRenderer>;
      try {
        renderer = new T.WebGLRenderer({
          alpha: true,
          antialias: true,
          powerPreference: "low-power",
        });
      } catch {
        return;
      }
      renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
      el.append(renderer.domElement);
      const scene = new T.Scene(),
        camera = new T.PerspectiveCamera(38, 1, 0.1, 100);
      camera.position.z = 6;
      const group = new T.Group();
      scene.add(group);
      const geometries: InstanceType<typeof T.BufferGeometry>[] = [],
        materials: InstanceType<typeof T.Material>[] = [];
      const rings = [1.25, 1.05, 0.72];
      rings.forEach((r, i) => {
        const g = new T.TorusGeometry(r, i === 0 ? 0.025 : 0.06, 16, 96);
        const m = new T.MeshStandardMaterial({
          color: i === 1 ? 0xdbff48 : 0xded4e6,
          metalness: 0.8,
          roughness: 0.2,
        });
        const ring = new T.Mesh(g, m);
        ring.rotation.y = i * 0.3;
        ring.rotation.x = i * 0.25;
        group.add(ring);
        geometries.push(g);
        materials.push(m);
      });
      const core = new T.Group();
      group.add(core);
      const g = new T.IcosahedronGeometry(0.55, 2),
        m = new T.MeshPhysicalMaterial({
          color: 0xb7c68e,
          metalness: 0.25,
          roughness: 0.18,
          transparent: true,
          opacity: 0.7,
          wireframe: true,
        });
      const intactCore = new T.Mesh(g, m);
      core.add(intactCore);
      geometries.push(g);
      materials.push(m);
      const seamGeometry = new T.TorusGeometry(0.55, 0.018, 8, 64);
      const halfMaterial = m.clone();
      halfMaterial.opacity = 0;
      const seamMaterial = new T.MeshBasicMaterial({
        color: 0xffb466,
        transparent: true,
        opacity: 0,
        depthWrite: false,
      });
      const halves = [0, 1].map((index) => {
        const halfGeometry = new T.SphereGeometry(
          0.55,
          12,
          12,
          index * Math.PI,
          Math.PI,
        );
        const half = new T.Group();
        half.add(new T.Mesh(halfGeometry, halfMaterial));
        half.add(new T.Mesh(seamGeometry, seamMaterial));
        half.visible = false;
        core.add(half);
        geometries.push(halfGeometry);
        return half;
      });
      geometries.push(seamGeometry);
      materials.push(seamMaterial, halfMaterial);
      scene.add(new T.HemisphereLight(0xffffff, 0x312334, 3));
      const light = new T.PointLight(0xdbff48, 35);
      light.position.set(2, 3, 4);
      scene.add(light);
      const stars = new T.BufferGeometry(),
        positions = new Float32Array(120 * 3);
      for (let i = 0; i < positions.length; i++)
        positions[i] = Math.sin(i * 91.78) * 2.2;
      stars.setAttribute("position", new T.BufferAttribute(positions, 3));
      const starMat = new T.PointsMaterial({
        color: 0xd9f89f,
        size: 0.017,
        transparent: true,
        opacity: 0.6,
      });
      const points = new T.Points(stars, starMat);
      group.add(points);
      geometries.push(stars);
      materials.push(starMat);
      const orbit = new T.Group();
      group.add(orbit);
      const orbitPath = new T.EllipseCurve(
        0,
        0,
        1.7,
        1.15,
        0,
        Math.PI * 2,
        false,
        0,
      );
      const orbitGeometry = new T.BufferGeometry().setFromPoints(
        orbitPath.getPoints(100).map((p) => new T.Vector3(p.x, p.y, 0)),
      );
      const orbitMaterial = new T.LineDashedMaterial({
        color: 0xdbff48,
        transparent: true,
        opacity: 0.28,
        dashSize: 0.05,
        gapSize: 0.08,
      });
      const orbitLine = new T.Line(orbitGeometry, orbitMaterial);
      orbitLine.computeLineDistances();
      orbit.rotation.x = 0.8;
      orbit.rotation.z = -0.4;
      orbit.add(orbitLine);
      const satelliteGeometry = new T.SphereGeometry(0.055, 12, 8);
      const satelliteMaterial = new T.MeshBasicMaterial({ color: 0xf0ffb0 });
      const satellites = [0, 1, 2].map(() => {
        const mesh = new T.Mesh(satelliteGeometry, satelliteMaterial);
        orbit.add(mesh);
        return mesh;
      });
      geometries.push(orbitGeometry, satelliteGeometry);
      materials.push(orbitMaterial, satelliteMaterial);
      let x = 0,
        y = 0,
        userY = 0.35,
        userX = 0.15,
        drag = false,
        visible = true,
        dirty = true,
        frame = 0,
        last = 0;
      let hasRevealed = false;
      const rotate = (horizontal: number, vertical: number) => {
        userY += horizontal;
        userX += vertical;
        dirty = true;
      };
      const resize = () => {
        const b = el.getBoundingClientRect();
        renderer.setSize(b.width, b.height);
        camera.aspect = b.width / b.height;
        camera.updateProjectionMatrix();
        dirty = true;
      };
      const ro = new ResizeObserver(resize);
      ro.observe(el);
      resize();
      const down = (e: PointerEvent) => {
        drag = true;
        el.setPointerCapture(e.pointerId);
        x = e.clientX;
        y = e.clientY;
      };
      const move = (e: PointerEvent) => {
        if (drag) {
          rotate((e.clientX - x) * 0.012, (e.clientY - y) * 0.012);
          x = e.clientX;
          y = e.clientY;
        }
      };
      const up = () => {
        drag = false;
      };
      const keydown = (e: KeyboardEvent) => {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        rotate(e.key === "ArrowLeft" ? -0.18 : 0.18, 0);
      };
      el.addEventListener("pointerdown", down);
      el.addEventListener("pointermove", move);
      el.addEventListener("pointerup", up);
      el.addEventListener("pointercancel", up);
      el.addEventListener("lostpointercapture", up);
      el.addEventListener("keydown", keydown);
      const io = new IntersectionObserver(
        (es) => (visible = es[0].isIntersecting),
      );
      io.observe(el);
      const draw = (t: number) => {
        const activeMotion = motionState.current;
        frame = requestAnimationFrame(draw);
        if (document.hidden || !visible || t - last < 32) return;
        last = t;
        group.rotation.y =
          userY + (activeMotion && !drag ? Math.sin(t * 0.0003) * 0.28 : 0);
        group.rotation.x = userX;
        const target = expanded.current ? 1.33 : 1;
        if (
          !activeMotion &&
          !drag &&
          !dirty &&
          Math.abs(group.scale.x - target) < 0.002
        )
          return;
        dirty = false;
        const side = Math.abs(Math.sin(userY));
        const exposure = Math.min(1, Math.max(0, (side - 0.57) / 0.39));
        const opening = exposure * exposure * (3 - 2 * exposure);
        const showSeam = hasRevealed ? opening > 0.22 : opening > 0.4;
        if (showSeam !== hasRevealed) {
          hasRevealed = showSeam;
          setRevealed(showSeam);
        }
        core.rotation.y = -Math.sin(userY) * opening * 0.22;
        m.opacity = 0.7 * (1 - opening);
        halfMaterial.opacity = 0.7 * opening;
        intactCore.visible = opening < 0.999;
        seamMaterial.opacity = opening;
        halves.forEach((half, index) => {
          half.visible = opening > 0;
          half.position.z = (index === 0 ? 1 : -1) * opening * 0.22;
        });
        if (!activeMotion) group.scale.setScalar(target);
        group.scale.lerp(new T.Vector3(target, target, target), 0.07);
        points.rotation.z += activeMotion ? 0.001 : 0;
        satellites.forEach((satellite, i) => {
          const phase =
            (activeMotion ? t * 0.00035 : 0) + (i * Math.PI * 2) / 3;
          satellite.position.set(
            Math.cos(phase) * 1.7,
            Math.sin(phase) * 1.15,
            0,
          );
        });
        renderer.render(scene, camera);
      };
      frame = requestAnimationFrame(draw);
      setReady(true);
      cleanup = () => {
        cancelAnimationFrame(frame);
        ro.disconnect();
        io.disconnect();
        el.removeEventListener("pointerdown", down);
        el.removeEventListener("pointermove", move);
        el.removeEventListener("pointerup", up);
        el.removeEventListener("pointercancel", up);
        el.removeEventListener("lostpointercapture", up);
        el.removeEventListener("keydown", keydown);
        geometries.forEach((g) => g.dispose());
        materials.forEach((m) => m.dispose());
        renderer.dispose();
        renderer.forceContextLoss();
        renderer.domElement.remove();
      };
    });
    return () => {
      disposed = true;
      cleanup();
    };
  }, []);
  return (
    <div className={"lens-widget " + (open ? "is-expanded" : "")}>
      <div className="lens-widget-top">
        <span className="live-dot" /> PAUSE. CHECK. CONNECT.
      </div>
      <div
        ref={host}
        className="lens-canvas"
        role={ready ? "group" : "img"}
        tabIndex={ready ? 0 : undefined}
        aria-label={
          ready ? "拖动或按左右方向键旋转真鉴透镜" : "真鉴透镜示意"
        }
      >
        {!ready && (
          <div className="lens-fallback">
            <i />
            <i />
            <Icon name="lens" />
          </div>
        )}
      </div>
      <div className="lens-widget-bottom">
        <span aria-live="polite">
          {revealed
            ? "转个角度，破绽就露出来了。有疑问，先排查，核实后再行动。"
            : !ready
              ? "多一次确认，多一份安心"
              : "拖动透镜，换个角度看"}
        </span>
        <button
          className="icon-button"
          aria-label={open ? "收拢透镜" : "展开透镜"}
          aria-pressed={open}
          onClick={() => {
            expanded.current = !open;
            setOpen(!open);
          }}
        >
          <Icon name={open ? "close" : "plus"} />
        </button>
      </div>
    </div>
  );
}
