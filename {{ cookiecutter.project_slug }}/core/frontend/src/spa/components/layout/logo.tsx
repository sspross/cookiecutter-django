interface LogoProps {
  label?: string;
  className?: string;
}

/**
 * Mirror of core/templates/_logo.html so Django-rendered pages (login)
 * share the same mark as the SPA. Update both together.
 */
export function Logo({ label = "{{ cookiecutter.project_name }}", className }: LogoProps) {
  const initial = label.charAt(0).toUpperCase();
  return (
    <div
      className={
        "flex flex-col items-center text-foreground" +
        (className ? ` ${className}` : "")
      }
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <span className="text-lg font-semibold tracking-tight">{initial}</span>
      </div>
      <span className="mt-1 text-[10px] font-medium uppercase tracking-wider">
        {label}
      </span>
    </div>
  );
}
