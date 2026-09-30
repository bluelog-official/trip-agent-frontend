import { useTranslation } from "react-i18next";
import { BUDGET_FILTERS, DURATION_FILTERS } from "../../lib/magazineMatrix";

function FilterRow({ id, label, options, value, onChange }) {
  const { t } = useTranslation();
  return (
    <div className="magazine-filter-row">
      <span className="magazine-filter-label" id={`${id}-label`}>
        {label}
      </span>
      <div className="magazine-filter-chips" role="radiogroup" aria-labelledby={`${id}-label`}>
        {options.map((option) => {
          const active = option.id === value;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={active}
              className={active ? "is-active" : ""}
              onClick={() => onChange(option.id)}
            >
              {t(option.labelKey)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function MagazineFilters({ duration, budget, onDuration, onBudget }) {
  const { t } = useTranslation();
  return (
    <div className="magazine-filters">
      <FilterRow
        id="duration"
        label={t("matrix.durationLabel")}
        options={DURATION_FILTERS}
        value={duration}
        onChange={onDuration}
      />
      <FilterRow
        id="budget"
        label={t("matrix.budgetLabel")}
        options={BUDGET_FILTERS}
        value={budget}
        onChange={onBudget}
      />
    </div>
  );
}
