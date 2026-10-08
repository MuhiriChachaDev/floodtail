import Image from "next/image";
import { clsx } from "clsx";

type Variant = "color" | "white";

type Props = {
  variant?: Variant;
  className?: string;
  /** Height in CSS (width scales). Default matches header. */
  heightClass?: string;
  priority?: boolean;
};

const SRC: Record<Variant, string> = {
  color: "/brand/kenya-re-logo.png",
  white: "/brand/kenya-re-logo-white.png",
};

/** Official Kenya Re mark from kenyare.co.ke (local copy under /public/brand). */
export function KenyaReLogo({
  variant = "white",
  className,
  heightClass = "h-9",
  priority = false,
}: Props) {
  return (
    <Image
      src={SRC[variant]}
      alt="Kenya Re"
      width={595}
      height={316}
      priority={priority}
      className={clsx(heightClass, "w-auto object-contain", className)}
    />
  );
}
