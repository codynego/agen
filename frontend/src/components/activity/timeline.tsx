import type { DashboardSnapshot } from "@/lib/types";

export function Timeline({ snapshot }: { snapshot: DashboardSnapshot }) {
  return (
    <div className="timeline">
      {snapshot.recent_activity.map((item) => (
        <div key={`${item.title}-${item.created_at}`} className="timeline__item">
          <div className="timeline__time">{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
          <div>
            <p className="timeline__title">{item.title}</p>
            <p className="timeline__detail">{item.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

