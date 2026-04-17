// Content script — runs in page context. Scope is deliberately tiny:
//
//   - Listen for <form> submit events.
//   - Extract ONLY the form's `name` / `id` attribute and the NAMES of each
//     input/select/textarea inside it.
//   - Forward those names to the service worker.
//
// The `value`, `innerText`, attribute data- values, and any surrounding DOM
// MUST NOT be read. This file is intentionally short so that a reviewer can
// verify the above invariant at a glance.

(() => {
  function fieldNamesOf(form) {
    const names = [];
    for (const el of form.elements) {
      if (!el) continue;
      const n = el.getAttribute?.("name") || el.getAttribute?.("id");
      if (n && typeof n === "string") names.push(n);
    }
    return names;
  }

  document.addEventListener(
    "submit",
    (ev) => {
      const form = ev.target;
      if (!(form instanceof HTMLFormElement)) return;
      try {
        chrome.runtime.sendMessage({
          type: "ant.form.submit",
          formName: form.getAttribute("name") || form.getAttribute("id") || "",
          fieldNames: fieldNamesOf(form),
        });
      } catch {
        // Extension context may be invalidated during reload; never throw.
      }
    },
    { capture: true, passive: true },
  );
})();
