import { Card } from "@/components/ui/card";

type MetricGridProps = {
  metrics: Array<{ label: string; value: number; hint: string }>;
};

export function MetricGrid({ metrics }: MetricGridProps) {
  return (
    <div className="grid grid--metrics">
      {metrics.map((metric) => (
        <Card key={metric.label} className="metric">
          <p className="metric__label">{metric.label}</p>
          <p className="metric__value">{metric.value.toLocaleString()}</p>
          <p className="metric__trend">{metric.hint}</p>
        </Card>
      ))}
    </div>
  );
}

