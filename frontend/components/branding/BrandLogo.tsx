import Image from "next/image";
import Link from "next/link";
import styles from "./BrandLogo.module.css";

type BrandLogoProps = {
  href?: string;
  theme?: "dark" | "light";
  tagline?: string;
  compact?: boolean;
  className?: string;
};

export default function BrandLogo({
  href = "/",
  theme = "dark",
  tagline,
  compact = false,
  className = "",
}: BrandLogoProps) {
  return (
    <Link
      href={href}
      aria-label="SnapTracer home"
      className={[styles.logo, theme === "light" ? styles.light : styles.dark, compact ? styles.compact : "", className].filter(Boolean).join(" ")}
    >
      <Image src="/favicon.svg" alt="" width={44} height={44} className={styles.mark} />
      <span className={styles.copy}>
        <span className={styles.name}>SnapTracer</span>
        {tagline && <span className={styles.tagline}>{tagline}</span>}
      </span>
    </Link>
  );
}
