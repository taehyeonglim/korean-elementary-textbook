/**
 * Shared client-side state for the subject archive filters.
 *
 * Fields are ordered from broad to specific (grade band → domain → module).
 * A value is available only when it can produce at least one workbook with
 * the selected broader fields, and an invalid dependent value is cleared
 * rather than leaving the user at an empty result set.
 */

/**
 * @param {Record<string, string>} record
 * @param {Record<string, string>} values
 * @param {string[]} fields
 */
export function matchesFilters(record, values, fields) {
  return fields.every((field) => !values[field] || record[field] === values[field]);
}

/**
 * Return values for one field that remain possible with earlier (broader)
 * selections. This hierarchy lets a new domain selection take precedence over
 * an older module value.
 *
 * @param {Record<string, string>[]} records
 * @param {Record<string, string>} values
 * @param {string} field
 * @param {string[]} fields
 */
export function availableValuesFromUpstream(records, values, field, fields) {
  const fieldIndex = fields.indexOf(field);
  const upstreamFields = fieldIndex < 0 ? [] : fields.slice(0, fieldIndex);
  const valuesForField = new Set();
  records.forEach((record) => {
    const matchesUpstream = upstreamFields.every((upstreamField) =>
      !values[upstreamField] || record[upstreamField] === values[upstreamField]
    );
    if (matchesUpstream && record[field]) valuesForField.add(record[field]);
  });
  return valuesForField;
}

/**
 * Clear only invalid dependent selections. The first field is the broadest
 * condition and is intentionally kept; later fields are checked only against
 * earlier fields, then safely fall back to their "all" option when an earlier
 * condition rules them out.
 *
 * @param {Record<string, string>[]} records
 * @param {Record<string, string>} inputValues
 * @param {string[]} fields
 */
export function normalizeFilters(records, inputValues, fields) {
  const values = Object.fromEntries(fields.map((field) => [field, String(inputValues[field] ?? "")]));
  fields.slice(1).forEach((field) => {
    if (values[field] && !availableValuesFromUpstream(records, values, field, fields).has(values[field])) values[field] = "";
  });
  return values;
}

/**
 * @typedef {{
 *   form: string,
 *   list: string,
 *   empty: string,
 *   count: string,
 *   fields: string[],
 *   resultLabel: string,
 *   persistUrl?: boolean,
 * }} CascadingFilterOptions
 */

/**
 * @param {CascadingFilterOptions} options
 */
export function initCascadingFilters(options) {
  const form = document.querySelector(options.form);
  const empty = document.querySelector(options.empty);
  const count = document.querySelector(options.count);
  if (!(form instanceof HTMLFormElement)) return;

  const selects = Object.fromEntries(options.fields.map((field) => {
    const element = form.elements.namedItem(field);
    return [field, element instanceof HTMLSelectElement ? element : null];
  }));
  if (Object.values(selects).some((select) => !select)) return;

  const items = Array.from(document.querySelectorAll(options.list));
  const entries = items.map((item) => {
    const card = item.querySelector("[data-grade-band]");
    return {
      item,
      record: Object.fromEntries(options.fields.map((field) => [field, card?.dataset[field] ?? ""])),
    };
  });
  const records = entries.map(({ record }) => record);

  const readValues = () => Object.fromEntries(options.fields.map((field) => [field, selects[field].value]));
  const writeValues = (values) => options.fields.forEach((field) => { selects[field].value = values[field]; });

  const updateOptions = (values) => {
    options.fields.forEach((field) => {
      // Options follow the same broad-to-specific hierarchy as normalization.
      const enabledValues = availableValuesFromUpstream(records, values, field, options.fields);
      Array.from(selects[field].options).forEach((option) => {
        if (!option.value) return;
        const available = enabledValues.has(option.value);
        option.disabled = !available;
        option.hidden = !available;
      });
    });
  };

  const updateUrl = (mode) => {
    if (options.persistUrl === false) return;
    const next = new URL(window.location.href);
    const values = readValues();
    options.fields.forEach((field) => {
      if (values[field]) next.searchParams.set(field, values[field]);
      else next.searchParams.delete(field);
    });
    const href = `${next.pathname}${next.search}${next.hash}`;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (href !== current) window.history[mode === "push" ? "pushState" : "replaceState"](null, "", href);
  };

  const apply = () => {
    const values = readValues();
    let visible = 0;
    entries.forEach(({ item, record }) => {
      const matches = matchesFilters(record, values, options.fields);
      item.hidden = !matches;
      if (matches) visible += 1;
    });
    updateOptions(values);
    if (empty instanceof HTMLElement) empty.hidden = visible !== 0;
    if (count) count.textContent = `총 ${visible}개의 ${options.resultLabel}`;
  };

  const normalizeAndApply = () => {
    writeValues(normalizeFilters(records, readValues(), options.fields));
    apply();
  };

  const loadFromUrl = () => {
    const params = new URLSearchParams(window.location.search);
    options.fields.forEach((field) => {
      const requested = params.get(field) ?? "";
      const exists = Array.from(selects[field].options).some((option) => option.value === requested);
      selects[field].value = exists ? requested : "";
    });
    normalizeAndApply();
  };

  loadFromUrl();
  // Remove unknown or incompatible query values without creating a new history entry.
  updateUrl("replace");
  form.addEventListener("change", () => {
    normalizeAndApply();
    updateUrl("push");
  });
  form.addEventListener("reset", () => {
    window.requestAnimationFrame(() => {
      normalizeAndApply();
      updateUrl("push");
    });
  });
  window.addEventListener("popstate", () => {
    loadFromUrl();
    updateUrl("replace");
  });
}
