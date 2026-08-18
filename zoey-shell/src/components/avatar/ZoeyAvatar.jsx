const STATE_META = {
  idle: { color: "#62676f", speed: "6s", scale: 1 },
  listening: { color: "#8fa3ff", speed: "2.2s", scale: 1.04 },
  thinking: { color: "#c9b3ff", speed: "1.4s", scale: 1.06 },
  executing: { color: "#d9a15b", speed: "1.8s", scale: 1.05 },
  completed: { color: "#6fcf97", speed: "5s", scale: 1 },
  failed: { color: "#e2685f", speed: "5s", scale: 1 },
};

export default function ZoeyAvatar({ state = "idle", size = 26 }) {
  const meta = STATE_META[state] ?? STATE_META.idle;

  return (
    <span
      className="relative inline-flex shrink-0 items-center justify-center rounded-full"
      style={{ width: size, height: size }}
    >
      <span
        className="absolute inset-0 rounded-full opacity-40 blur-[6px] transition-colors duration-500"
        style={{
          background: meta.color,
          animation: `zoey-breathe ${meta.speed} ease-in-out infinite`,
        }}
      />
      <span
        className="relative rounded-full transition-colors duration-500"
        style={{
          width: size * 0.62,
          height: size * 0.62,
          background: `radial-gradient(circle at 35% 30%, ${meta.color}, ${meta.color}cc 60%, ${meta.color}88)`,
          transform: `scale(${meta.scale})`,
          transition: "transform 0.6s ease, background 0.5s ease",
        }}
      />
      <style>{`
        @keyframes zoey-breathe {
          0%, 100% { transform: scale(0.9); opacity: 0.3; }
          50% { transform: scale(1.15); opacity: 0.5; }
        }
      `}</style>
    </span>
  );
}
