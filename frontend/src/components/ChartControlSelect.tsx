import { ChevronDown } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

export type ChartControlSelectOption = {
  value: string;
  label: string;
};

type ChartControlSelectProps = {
  ariaLabel: string;
  options: ChartControlSelectOption[];
  value: string;
  onChange: (value: string) => void;
};

export function ChartControlSelect({
  ariaLabel,
  options,
  value,
  onChange,
}: ChartControlSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const listboxId = useId();
  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? options[0] ?? null,
    [options, value],
  );

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    window.addEventListener("pointerdown", handlePointerDown);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
    };
  }, []);

  return (
    <div className={`chart-custom-select${isOpen ? " is-open" : ""}`} ref={rootRef}>
      <button
        aria-controls={isOpen ? listboxId : undefined}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        className="chart-custom-select-trigger"
        onClick={() => setIsOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setIsOpen(true);
          }

          if (event.key === "Escape") {
            event.preventDefault();
            setIsOpen(false);
          }
        }}
        type="button"
      >
        <span className="chart-custom-select-value">{selectedOption?.label ?? ""}</span>
        <ChevronDown aria-hidden="true" className="chart-custom-select-icon" size={16} strokeWidth={1.9} />
      </button>
      {isOpen ? (
        <div
          aria-label={ariaLabel}
          className="chart-custom-select-menu"
          id={listboxId}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              setIsOpen(false);
            }
          }}
          role="listbox"
        >
          {options.map((option) => {
            const isSelected = option.value === value;

            return (
              <button
                aria-selected={isSelected}
                className={`chart-custom-select-option${isSelected ? " is-selected" : ""}`}
                key={option.value}
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
                role="option"
                type="button"
              >
                {option.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
