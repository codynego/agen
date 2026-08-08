import Link from "next/link";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = {
  variant?: ButtonVariant;
  href?: string;
  className?: string;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement> &
  AnchorHTMLAttributes<HTMLAnchorElement>;

export function Button({ variant = "primary", href, className = "", children, ...props }: ButtonProps) {
  const buttonClassName = `button button--${variant} ${className}`.trim();

  if (href) {
    return (
      <Link href={href} className={buttonClassName} {...props}>
        {children}
      </Link>
    );
  }

  return (
    <button type="button" className={buttonClassName} {...props}>
      {children}
    </button>
  );
}
