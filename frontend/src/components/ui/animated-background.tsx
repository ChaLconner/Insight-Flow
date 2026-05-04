"use client";

import { useEffect, useRef, useState } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  color: string;
}

interface AnimatedBackgroundProps {
  className?: string;
}

export function AnimatedBackground({
  className = "",
}: AnimatedBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const particlesRef = useRef<Particle[]>([]);
  const mouseRef = useRef({ x: 0, y: 0 });


  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) {
      return;
    }

    // Mutable ref so recoverAnimation can swap in a fresh context.
    const activeCtx = { current: ctx };

    let lastFrameAt = 0;

    const resizeCanvas = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      const sizeChanged = canvas.width !== width || canvas.height !== height;

      if (sizeChanged) {
        canvas.width = width;
        canvas.height = height;
      }

      return sizeChanged;
    };

    // Create particles
    const createParticles = () => {
      const particleCount = Math.floor((canvas.width * canvas.height) / 15000);
      particlesRef.current = [];

      for (let i = 0; i < particleCount; i++) {
        particlesRef.current.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          vx: (Math.random() - 0.5) * 0.5,
          vy: (Math.random() - 0.5) * 0.5,
          size: Math.random() * 3 + 1,
          opacity: Math.random() * 0.5 + 0.2,
          color:
            Math.random() > 0.7
              ? "#6366f1"
              : Math.random() > 0.5
                ? "#8b5cf6"
                : "#64748b",
        });
      }
    };

    const handleResize = () => {
      if (resizeCanvas()) {
        createParticles();
      }
    };

    // Mouse interaction
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = e.clientX;
      mouseRef.current.y = e.clientY;
    };

    // Animation loop
    const animate = () => {
      activeCtx.current.clearRect(0, 0, canvas.width, canvas.height);

      const particles = particlesRef.current;
      const connectionDistance = 120;
      const cellSize = connectionDistance;
      const grid = new Map<string, number[]>();

      const getCellKey = (x: number, y: number) =>
        `${Math.floor(x / cellSize)}:${Math.floor(y / cellSize)}`;

      // Update particles first so connection checks use stable positions.
      particles.forEach((particle, index) => {
        // Update position
        particle.x += particle.vx;
        particle.y += particle.vy;

        // Wrap around edges
        if (particle.x < 0) {
          particle.x = canvas.width;
        }
        if (particle.x > canvas.width) {
          particle.x = 0;
        }
        if (particle.y < 0) {
          particle.y = canvas.height;
        }
        if (particle.y > canvas.height) {
          particle.y = 0;
        }

        // Mouse interaction - repel particles
        const dx = mouseRef.current.x - particle.x;
        const dy = mouseRef.current.y - particle.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance > 0 && distance < 100) {
          const force = (100 - distance) / 100;
          particle.vx -= (dx / distance) * force * 0.02;
          particle.vy -= (dy / distance) * force * 0.02;
        } else {
          // Slow down when not near mouse
          particle.vx *= 0.99;
          particle.vy *= 0.99;
        }

        const cellKey = getCellKey(particle.x, particle.y);
        const cell = grid.get(cellKey);
        if (cell) {
          cell.push(index);
        } else {
          grid.set(cellKey, [index]);
        }
      });

      // Draw particles and nearby connections.
      particles.forEach((particle, index) => {
        // Draw particle
        const drawCtx = activeCtx.current;
        drawCtx.save();
        drawCtx.globalAlpha = particle.opacity;
        drawCtx.fillStyle = particle.color;
        drawCtx.beginPath();
        drawCtx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        drawCtx.fill();

        // Add glow effect
        drawCtx.shadowColor = particle.color;
        drawCtx.shadowBlur = particle.size * 2;
        drawCtx.fill();
        drawCtx.restore();

        // Draw connections
        const cellX = Math.floor(particle.x / cellSize);
        const cellY = Math.floor(particle.y / cellSize);
        for (let offsetX = -1; offsetX <= 1; offsetX += 1) {
          for (let offsetY = -1; offsetY <= 1; offsetY += 1) {
            const nearby = grid.get(`${cellX + offsetX}:${cellY + offsetY}`);
            if (!nearby) {
              continue;
            }

            nearby.forEach((otherIndex) => {
              if (otherIndex <= index) {
                return;
              }

              const otherParticle = particles[otherIndex];
              const dx = particle.x - otherParticle.x;
              const dy = particle.y - otherParticle.y;
              const distance = Math.sqrt(dx * dx + dy * dy);

              if (distance < connectionDistance) {
                drawCtx.save();
                drawCtx.globalAlpha = ((connectionDistance - distance) / connectionDistance) * 0.1;
                drawCtx.strokeStyle = "#6366f1";
                drawCtx.lineWidth = 1;
                drawCtx.beginPath();
                drawCtx.moveTo(particle.x, particle.y);
                drawCtx.lineTo(otherParticle.x, otherParticle.y);
                drawCtx.stroke();
                drawCtx.restore();
              }
            });
          }
        }
      });

      animationRef.current = requestAnimationFrame(animate);
      lastFrameAt = performance.now();
    };

    const stopAnimation = () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = undefined;
      }
    };

    const startAnimation = (force = false) => {
      const frameStale =
        lastFrameAt > 0 && performance.now() - lastFrameAt > 1000;

      if (force || frameStale) {
        stopAnimation();
      } else if (animationRef.current) {
        return;
      }

      if (resizeCanvas()) {
        createParticles();
      } else if (particlesRef.current.length === 0) {
        createParticles();
      }

      animate();
    };

    const recoverAnimation = () => {
      // Re-acquire context in case the canvas bitmap was cleared by
      // bfcache or visibility changes. The old ctx ref may be stale.
      const freshCtx = canvas.getContext("2d", { willReadFrequently: true });
      if (freshCtx) {
        activeCtx.current = freshCtx;
      }
      if (resizeCanvas() || particlesRef.current.length === 0) {
        createParticles();
      }
      startAnimation(true);
    };

    const ensureAnimationHealthy = () => {
      if (document.hidden) {
        return;
      }

      const frameStale =
        lastFrameAt > 0 && performance.now() - lastFrameAt > 1000;
      const canvasSizeMismatch =
        canvas.width !== window.innerWidth || canvas.height !== window.innerHeight;

      if (!animationRef.current || frameStale || canvasSizeMismatch) {
        recoverAnimation();
      }
    };

    // Initialize
    resizeCanvas();
    createParticles();
    startAnimation();

    // Event listeners
    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);

    // Visibility/page lifecycle handlers keep the canvas alive across bfcache
    // restores. Do not cancel RAF on hide; some browsers restore the page
    // without replaying timers/listeners soon enough, leaving the canvas at
    // its default 300x150 backing size until a full reload.
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        recoverAnimation();
      }
    };

    const handlePageShow = () => {
      recoverAnimation();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pageshow", handlePageShow);
    window.addEventListener("focus", recoverAnimation);
    window.addEventListener("pointermove", ensureAnimationHealthy, { passive: true });
    window.addEventListener("mousemove", ensureAnimationHealthy, { passive: true });
    window.addEventListener("click", ensureAnimationHealthy);
    const healthCheckInterval = window.setInterval(ensureAnimationHealthy, 750);

    // Cleanup
    return () => {
      stopAnimation();
      window.clearInterval(healthCheckInterval);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pageshow", handlePageShow);
      window.removeEventListener("focus", recoverAnimation);
      window.removeEventListener("pointermove", ensureAnimationHealthy);
      window.removeEventListener("mousemove", ensureAnimationHealthy);
      window.removeEventListener("click", ensureAnimationHealthy);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 h-screen w-screen pointer-events-none z-0 ${className}`}
      style={{ background: "transparent", height: "100vh", width: "100vw" }}
    />
  );
}

// Floating shapes component for additional visual appeal
export function FloatingShapes() {
  const [shapes, setShapes] = useState<
    Array<{ left: string; top: string; delay: string; duration: string }>
  >([]);

  useEffect(() => {
    setShapes(
      Array.from({ length: 20 }).map(() => ({
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        delay: `${Math.random() * 5}s`,
        duration: `${2 + Math.random() * 10}s`,
      })),
    );
  }, []);

  if (shapes.length === 0) {
    return null;
  }

  return (
    <div className="fixed inset-0 pointer-events-none z-10">
      {/* Dots pattern */}
      <div className="absolute inset-0 opacity-30">
        {shapes.map((shape, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-indigo-400/40 rounded-full animate-pulse"
            style={{
              left: shape.left,
              top: shape.top,
              animationDelay: shape.delay,
              animationDuration: shape.duration,
            }}
          />
        ))}
      </div>
    </div>
  );
}
