import { useRef, type KeyboardEvent } from "react";
import styles from "./SegmentedControl.module.css";

interface SegmentedControlProps<T extends string> {
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}

/** Radio-group style toggle with roving focus and arrow-key navigation. */
export function SegmentedControl<T extends string>({ options, value, onChange, label }: SegmentedControlProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = (e: KeyboardEvent, index: number) => {
    const delta = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!delta) return;
    e.preventDefault();
    const next = (index + delta + options.length) % options.length;
    onChange(options[next]);
    refs.current[next]?.focus();
  };

  return (
    <div role="radiogroup" aria-label={label} className={styles.group}>
      {options.map((opt, i) => {
        const checked = opt === value;
        return (
          <button
            key={opt}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            className={[styles.option, checked ? styles.checked : ""].join(" ")}
            onClick={() => onChange(opt)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}
