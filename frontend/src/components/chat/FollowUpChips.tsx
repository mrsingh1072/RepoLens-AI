import { Overline } from "@/components/common/Overline";

interface FollowUpChipsProps {
  suggestions: string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
}

export function FollowUpChips({ suggestions, onSelect, disabled }: FollowUpChipsProps) {
  if (!suggestions.length) return null;

  return (
    <div className="w-full space-y-2 pt-1">
      <Overline>Follow-up</Overline>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(s.replace(/`/g, ""))}
            className="rounded-full border border-edge bg-raised px-3 py-1.5 text-left text-xs text-ink-2 transition-[transform,border-color,color] hover:border-ember/40 hover:text-ink active:scale-[0.98] disabled:opacity-50"
          >
            {s.replace(/`/g, "")}
          </button>
        ))}
      </div>
    </div>
  );
}
