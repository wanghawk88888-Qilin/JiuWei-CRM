type BadgeVariant =
  | "default"
  | "blue"
  | "green"
  | "yellow"
  | "red"
  | "purple"
  | "gray";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-700",
  blue: "bg-blue-100 text-blue-700",
  green: "bg-green-100 text-green-700",
  yellow: "bg-yellow-100 text-yellow-700",
  red: "bg-red-100 text-red-700",
  purple: "bg-purple-100 text-purple-700",
  gray: "bg-gray-200 text-gray-600",
};

// Map status to badge color
export function statusBadgeVariant(status: string): BadgeVariant {
  switch (status) {
    case "new":
      return "blue";
    case "consulted":
      return "yellow";
    case "following":
      return "purple";
    case "high_intent":
      return "green";
    case "enrolled":
      return "green";
    case "invalid":
      return "gray";
    default:
      return "default";
  }
}

// Map intention level to badge color
export function intentionBadgeVariant(level: string): BadgeVariant {
  switch (level) {
    case "high":
      return "green";
    case "medium":
      return "yellow";
    case "low":
      return "gray";
    default:
      return "default";
  }
}

export default function Badge({
  variant = "default",
  className = "",
  children,
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
