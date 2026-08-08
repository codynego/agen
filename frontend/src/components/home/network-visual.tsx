import { Card } from "@/components/ui/card";

const nodes = [
  { label: "Personal Agent", left: "50%", top: "16%" },
  { label: "Hotel Agent", left: "16%", top: "58%" },
  { label: "Finance Agent", left: "50%", top: "60%" },
  { label: "Retail Agent", left: "82%", top: "58%" },
];

export function NetworkVisual() {
  return (
    <Card className="network">
      <div className="network__canvas" aria-hidden="true" />
      <span className="network__line" style={{ left: "24%", top: "48%", width: "52%", transform: "rotate(0deg)" }} />
      <span className="network__line" style={{ left: "24%", top: "48%", width: "16%", transform: "rotate(28deg)" }} />
      <span className="network__line" style={{ left: "50%", top: "28%", width: "18%", transform: "rotate(56deg)" }} />
      {nodes.map((node) => (
        <div
          key={node.label}
          className="node"
          style={{
            left: node.left,
            top: node.top,
            transform: "translate(-50%, -50%)",
          }}
        >
          <span className="node__dot" />
          <span className="node__label">{node.label}</span>
        </div>
      ))}
    </Card>
  );
}

