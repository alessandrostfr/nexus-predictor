import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';

import { FABRIK_MAP_CLEAN_BASE64 } from '../assets/fabrikMapCleanedBase64.js';

// Mapa calibrado sobre la imagen "Frame 2" que marcaste en Paint.
// La textura y los polígonos usan exactamente el mismo lienzo de 1002x523 px,
// por eso las zonas interactivas caen sobre las salas reales y no sobre cajas aproximadas.
const IMAGE_WIDTH = 1002;
const IMAGE_HEIGHT = 523;
const WORLD_WIDTH = 18;
const WORLD_HEIGHT = WORLD_WIDTH * (IMAGE_HEIGHT / IMAGE_WIDTH);
const BASE_Z = 0;

// Polígonos extraídos y simplificados desde tus contornos rojos.
// Cada punto está en coordenadas de píxel de la textura base.
const ROOM_AREAS = {
  hangar: {
    label: 'Hangar',
    points: [[510, 56], [499, 59], [461, 20], [424, 13], [311, 75], [300, 89], [333, 97], [372, 130]],
  },
  'open-air': {
    label: 'Open Air',
    points: [[152, 357], [295, 398], [383, 338], [348, 315], [341, 293], [303, 271], [257, 268], [205, 286], [195, 330]],
  },
  'crystal-area': {
    label: 'Crystal Area',
    points: [[521, 190], [530, 215], [544, 220], [581, 222], [602, 205], [612, 218], [619, 220], [636, 207], [634, 191], [613, 188], [592, 176], [564, 170], [551, 171]],
  },
  'main-room': {
    label: 'Main Room',
    points: [[678, 320], [624, 271], [564, 258], [379, 360], [437, 371], [497, 428]],
  },
  satelite: {
    label: 'Satelite',
    points: [[722, 392], [707, 368], [672, 363], [570, 419], [522, 455], [554, 461], [571, 481]],
  },
  'club-area': {
    label: 'Club Area',
    points: [[608, 249], [611, 256], [660, 281], [676, 278], [717, 252], [716, 248], [666, 218], [618, 238]],
  },
  'area-19': {
    label: 'Area 19',
    points: [[769, 54], [848, 124], [1001, 28], [965, 3], [851, 0]],
  },
};

const SUPPORT_AREAS = {
  'hotel-fabrik': {
    label: 'Hotel Fabrik',
    points: [[674, 222], [758, 202], [822, 238], [739, 286], [653, 256]],
  },
};

const PRESSURE_COLORS = {
  critical: 0xff4b4b,
  high: 0xff9f43,
  medium: 0xf7e36a,
  low: 0x62e6b9,
  calm: 0x8fb7ff,
};

const PRESSURE_LABELS = {
  critical: 'Crítico',
  high: 'Alto',
  medium: 'Medio',
  low: 'Bajo',
  calm: 'Tranquilo',
};

function pixelToWorld(x, y) {
  return {
    x: (x / IMAGE_WIDTH - 0.5) * WORLD_WIDTH,
    y: (0.5 - y / IMAGE_HEIGHT) * WORLD_HEIGHT,
  };
}

function colorForLevel(level) {
  return PRESSURE_COLORS[level] ?? PRESSURE_COLORS.calm;
}

function pressureLabel(level) {
  return PRESSURE_LABELS[level] ?? level ?? '—';
}

function roomScore(room) {
  return Math.round(Number(room?.room_pressure_score ?? 0));
}

function makePolygonGeometry(pixelPoints, z = 0.08) {
  const shapePoints = pixelPoints.map(([x, py]) => {
    const point = pixelToWorld(x, py);
    return new THREE.Vector2(point.x, point.y);
  });

  const triangles = THREE.ShapeUtils.triangulateShape(shapePoints, []);
  const positions = [];
  const indices = [];

  shapePoints.forEach((point) => {
    positions.push(point.x, point.y, z);
  });

  triangles.forEach((triangle) => {
    indices.push(triangle[0], triangle[1], triangle[2]);
  });

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingSphere();
  return geometry;
}

function makeLineGeometry(pixelPoints, z = 0.13) {
  const positions = [];
  [...pixelPoints, pixelPoints[0]].forEach(([x, py]) => {
    const point = pixelToWorld(x, py);
    positions.push(point.x, point.y, z);
  });

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  return geometry;
}

function makeRoomMaterial(room, selected = false, hovered = false) {
  const color = colorForLevel(room.pressure_level);
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: selected ? 0.50 : hovered ? 0.42 : 0.28,
    depthWrite: false,
    depthTest: false,
    side: THREE.DoubleSide,
  });
}

function makeSupportMaterial() {
  return new THREE.MeshBasicMaterial({
    color: 0xd9eef0,
    transparent: true,
    opacity: 0.10,
    depthWrite: false,
    depthTest: false,
    side: THREE.DoubleSide,
  });
}

function centroidFromPoints(pixelPoints) {
  const sum = pixelPoints.reduce((acc, [x, y]) => ({ x: acc.x + x, y: acc.y + y }), { x: 0, y: 0 });
  return pixelToWorld(sum.x / pixelPoints.length, sum.y / pixelPoints.length);
}

function roundRect(context, x, y, width, height, radius) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.arcTo(x + width, y, x + width, y + height, radius);
  context.arcTo(x + width, y + height, x, y + height, radius);
  context.arcTo(x, y + height, x, y, radius);
  context.arcTo(x, y, x + width, y, radius);
  context.closePath();
}

function makeLabelSprite(text, pixelPoints, selected = false) {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  const width = 300;
  const height = 70;
  canvas.width = width;
  canvas.height = height;

  context.clearRect(0, 0, width, height);
  context.fillStyle = selected ? 'rgba(4, 17, 27, 0.88)' : 'rgba(4, 17, 27, 0.66)';
  context.strokeStyle = selected ? 'rgba(145, 255, 240, 0.92)' : 'rgba(145, 255, 240, 0.28)';
  context.lineWidth = 2;
  roundRect(context, 8, 8, width - 16, height - 16, 16);
  context.fill();
  context.stroke();
  context.font = '800 22px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif';
  context.fillStyle = '#f7ffff';
  context.fillText(text, 24, 43);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false, depthTest: false });
  const sprite = new THREE.Sprite(material);
  const center = centroidFromPoints(pixelPoints);
  sprite.position.set(center.x, center.y, 0.34);
  sprite.scale.set(selected ? 1.55 : 1.32, selected ? 0.36 : 0.30, 1);
  sprite.renderOrder = selected ? 40 : 30;
  return { sprite, texture, material };
}

function makeRoomGroup(room, area, selected = false, hovered = false) {
  const color = colorForLevel(room.pressure_level);
  const group = new THREE.Group();

  const mesh = new THREE.Mesh(makePolygonGeometry(area.points), makeRoomMaterial(room, selected, hovered));
  mesh.userData = { slug: room.slug, type: 'room', room };
  mesh.renderOrder = selected ? 18 : 12;
  group.add(mesh);

  const border = new THREE.Line(
    makeLineGeometry(area.points),
    new THREE.LineBasicMaterial({
      color: selected ? 0xffffff : color,
      transparent: true,
      opacity: selected ? 0.95 : 0.78,
      depthTest: false,
    }),
  );
  border.renderOrder = selected ? 24 : 18;
  group.add(border);

  if (selected || hovered) {
    const glow = new THREE.Mesh(
      makePolygonGeometry(area.points, 0.11),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: selected ? 0.18 : 0.11,
        depthWrite: false,
        depthTest: false,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
      }),
    );
    glow.renderOrder = selected ? 22 : 16;
    group.add(glow);
  }

  const label = makeLabelSprite(area.label, area.points, selected);
  group.add(label.sprite);

  return { group, mesh, extraDisposables: [label.texture, label.material] };
}

function makeSupportGroup(area) {
  const group = new THREE.Group();
  const mesh = new THREE.Mesh(makePolygonGeometry(area.points, 0.055), makeSupportMaterial());
  mesh.renderOrder = 6;
  group.add(mesh);

  const border = new THREE.Line(
    makeLineGeometry(area.points, 0.095),
    new THREE.LineBasicMaterial({ color: 0xd9eef0, transparent: true, opacity: 0.22, depthTest: false }),
  );
  border.renderOrder = 9;
  group.add(border);
  return group;
}

function selectedCopy(selectedTimeLabel) {
  return selectedTimeLabel ? `Franja: ${selectedTimeLabel}` : 'Simulación por franja';
}

export function FabrikThreeMap({ rooms, supportAreas = [], selectedRoom, selectedTimeLabel, onSelectRoom }) {
  const containerRef = useRef(null);
  const [hoveredSlug, setHoveredSlug] = useState(null);
  const [hoveredRoom, setHoveredRoom] = useState(null);

  const normalizedSupportAreas = useMemo(
    () => (supportAreas.length > 0 ? supportAreas : [{ slug: 'hotel-fabrik', name: 'Hotel Fabrik' }]),
    [supportAreas],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06111b);

    const camera = new THREE.OrthographicCamera(-WORLD_WIDTH / 2, WORLD_WIDTH / 2, WORLD_HEIGHT / 2, -WORLD_HEIGHT / 2, 0.1, 80);
    camera.position.set(0, 0, 10);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    const root = new THREE.Group();
    scene.add(root);

    const textureLoader = new THREE.TextureLoader();
    const mapTexture = textureLoader.load(FABRIK_MAP_CLEAN_BASE64, () => render());
    mapTexture.colorSpace = THREE.SRGBColorSpace;
    mapTexture.anisotropy = Math.min(12, renderer.capabilities.getMaxAnisotropy());

    const mapGeometry = new THREE.PlaneGeometry(WORLD_WIDTH, WORLD_HEIGHT, 1, 1);
    const mapMaterial = new THREE.MeshBasicMaterial({
      map: mapTexture,
      transparent: true,
      opacity: 0.99,
      side: THREE.DoubleSide,
    });
    const mapPlane = new THREE.Mesh(mapGeometry, mapMaterial);
    mapPlane.position.z = BASE_Z;
    mapPlane.renderOrder = 1;
    root.add(mapPlane);

    const clickableMeshes = [];
    const disposables = [mapGeometry, mapMaterial, mapTexture];

    normalizedSupportAreas.forEach((area) => {
      const blueprint = SUPPORT_AREAS[area.slug];
      if (!blueprint) return;
      const group = makeSupportGroup(blueprint);
      root.add(group);
      group.traverse((child) => {
        if (child.geometry) disposables.push(child.geometry);
        if (child.material) disposables.push(child.material);
      });
    });

    rooms.forEach((room) => {
      const area = ROOM_AREAS[room.slug];
      if (!area) return;
      const isSelected = selectedRoom?.slug === room.slug;
      const isHovered = hoveredSlug === room.slug;
      const { group, mesh, extraDisposables } = makeRoomGroup(room, area, isSelected, isHovered);
      root.add(group);
      clickableMeshes.push(mesh);
      disposables.push(...extraDisposables);
      group.traverse((child) => {
        if (child.geometry) disposables.push(child.geometry);
        if (child.material) disposables.push(child.material);
      });
    });

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let pointerDown = null;
    let zoom = 1;
    let targetZoom = 1;
    let panX = 0;
    let panY = 0;
    let targetPanX = 0;
    let targetPanY = 0;
    let frameId = 0;
    let lastHoverSlug = null;

    function applyCameraBounds() {
      camera.zoom = zoom;
      camera.position.x = panX;
      camera.position.y = panY;
      camera.updateProjectionMatrix();
    }

    function resize() {
      const width = Math.max(320, container.clientWidth);
      const height = Math.max(300, Math.round(width * (IMAGE_HEIGHT / IMAGE_WIDTH)));
      renderer.setSize(width, height, false);
      camera.left = -WORLD_WIDTH / 2;
      camera.right = WORLD_WIDTH / 2;
      camera.top = WORLD_HEIGHT / 2;
      camera.bottom = -WORLD_HEIGHT / 2;
      applyCameraBounds();
      render();
    }

    function setPointerFromEvent(event) {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    }

    function hoveredMesh(event) {
      setPointerFromEvent(event);
      raycaster.setFromCamera(pointer, camera);
      return raycaster.intersectObjects(clickableMeshes, false)[0]?.object ?? null;
    }

    function updateHover(event) {
      const mesh = hoveredMesh(event);
      renderer.domElement.style.cursor = mesh ? 'pointer' : 'grab';
      const nextSlug = mesh?.userData?.slug ?? null;
      if (nextSlug === lastHoverSlug) return;
      lastHoverSlug = nextSlug;
      setHoveredSlug(nextSlug);

      if (!mesh) {
        setHoveredRoom(null);
        return;
      }

      const room = mesh.userData.room;
      setHoveredRoom({
        name: room.name,
        score: roomScore(room),
        level: pressureLabel(room.pressure_level),
      });
    }

    function handlePointerMove(event) {
      if (pointerDown) {
        const dx = event.clientX - pointerDown.x;
        const dy = event.clientY - pointerDown.y;
        if (Math.hypot(dx, dy) > 3) {
          pointerDown.moved = true;
          targetPanX = THREE.MathUtils.clamp(pointerDown.startPanX - dx * 0.012 / zoom, -2.8, 2.8);
          targetPanY = THREE.MathUtils.clamp(pointerDown.startPanY + dy * 0.012 / zoom, -1.8, 1.8);
        }
        return;
      }
      updateHover(event);
    }

    function handlePointerDown(event) {
      renderer.domElement.setPointerCapture?.(event.pointerId);
      pointerDown = {
        x: event.clientX,
        y: event.clientY,
        startPanX: targetPanX,
        startPanY: targetPanY,
        moved: false,
      };
      renderer.domElement.style.cursor = 'grabbing';
    }

    function handlePointerUp(event) {
      renderer.domElement.releasePointerCapture?.(event.pointerId);
      renderer.domElement.style.cursor = 'grab';
      const moved = pointerDown?.moved;
      pointerDown = null;
      if (moved) return;

      const mesh = hoveredMesh(event);
      if (mesh?.userData?.slug && typeof onSelectRoom === 'function') {
        onSelectRoom(mesh.userData.slug);
      }
    }

    function handlePointerLeave() {
      renderer.domElement.style.cursor = 'grab';
      lastHoverSlug = null;
      setHoveredSlug(null);
      setHoveredRoom(null);
    }

    function handleWheel(event) {
      event.preventDefault();
      targetZoom = THREE.MathUtils.clamp(targetZoom - event.deltaY * 0.0012, 0.9, 2.25);
    }

    function render() {
      renderer.render(scene, camera);
    }

    function animate() {
      zoom += (targetZoom - zoom) * 0.14;
      panX += (targetPanX - panX) * 0.16;
      panY += (targetPanY - panY) * 0.16;
      applyCameraBounds();
      renderer.render(scene, camera);
      frameId = window.requestAnimationFrame(animate);
    }

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();
    animate();

    renderer.domElement.addEventListener('pointermove', handlePointerMove);
    renderer.domElement.addEventListener('pointerdown', handlePointerDown);
    renderer.domElement.addEventListener('pointerup', handlePointerUp);
    renderer.domElement.addEventListener('pointercancel', handlePointerUp);
    renderer.domElement.addEventListener('pointerleave', handlePointerLeave);
    renderer.domElement.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      window.cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener('pointermove', handlePointerMove);
      renderer.domElement.removeEventListener('pointerdown', handlePointerDown);
      renderer.domElement.removeEventListener('pointerup', handlePointerUp);
      renderer.domElement.removeEventListener('pointercancel', handlePointerUp);
      renderer.domElement.removeEventListener('pointerleave', handlePointerLeave);
      renderer.domElement.removeEventListener('wheel', handleWheel);
      disposables.forEach((item) => item?.dispose?.());
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [rooms, normalizedSupportAreas, selectedRoom?.slug, selectedTimeLabel, onSelectRoom, hoveredSlug]);

  return (
    <div className="three-map-shell three-map-shell-polygons three-map-shell-precision">
      <div className="three-map-toolbar">
        <div>
          <strong>Visor Three.js · áreas calibradas</strong>
          <span>{selectedCopy(selectedTimeLabel)}</span>
        </div>
        <small>Rueda para zoom · arrastra para mover · clic sobre una sala</small>
      </div>
      <div ref={containerRef} className="three-map-canvas" aria-label="Mapa interactivo de Fabrik con áreas reales clicables" />
      <div className="three-map-footer">
        <span>
          {hoveredRoom
            ? `${hoveredRoom.name} · ${hoveredRoom.score}% · ${hoveredRoom.level}`
            : 'Áreas calibradas sobre tu referencia: sin bloques 3D, sin leyenda naranja y sin promoción inferior.'}
        </span>
        <div className="map-legend map-legend-modern">
          <span><i data-pressure="critical" /> Crítico</span>
          <span><i data-pressure="high" /> Alto</span>
          <span><i data-pressure="medium" /> Medio</span>
          <span><i data-pressure="low" /> Bajo</span>
          <span><i data-pressure="calm" /> Tranquilo</span>
        </div>
      </div>
    </div>
  );
}
