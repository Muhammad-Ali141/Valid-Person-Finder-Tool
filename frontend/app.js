(function () {
  const form = document.getElementById("searchForm");
  const companyInput = document.getElementById("company");
  const designationInput = document.getElementById("designation");
  const submitBtn = document.getElementById("submitBtn");
  const loadingEl = document.getElementById("loading");
  const resultEl = document.getElementById("result");
  const errorEl = document.getElementById("error");

  function hideAll() {
    loadingEl.classList.add("hidden");
    resultEl.classList.add("hidden");
    errorEl.classList.add("hidden");
  }

  function showLoading() {
    hideAll();
    loadingEl.classList.remove("hidden");
    submitBtn.disabled = true;
  }

  function showResult(data) {
    hideAll();
    submitBtn.disabled = false;
    if (data.found) {
      const conf = data.confidence_score;
      const confClass = conf >= 0.7 ? "high" : conf >= 0.4 ? "medium" : "low";
      const confLabel = conf >= 0.7 ? "High" : conf >= 0.4 ? "Medium" : "Low";
      resultEl.innerHTML =
        "<h2>Person found</h2>" +
        "<dl>" +
        "<dt>First name</dt><dd>" + escapeHtml(data.first_name || "—") + "</dd>" +
        "<dt>Last name</dt><dd>" + escapeHtml(data.last_name || "—") + "</dd>" +
        "<dt>Current title</dt><dd>" + escapeHtml(data.current_title || "—") + "</dd>" +
        "<dt>Source</dt><dd>" + (data.source_url
          ? '<a href="' + escapeAttr(data.source_url) + '" target="_blank" rel="noopener">' + escapeHtml(data.source_url) + "</a>"
          : "—") + "</dd>" +
        "<dt>Confidence</dt><dd><span class=\"confidence " + confClass + "\">" + confLabel + " (" + (data.confidence_score * 100).toFixed(0) + "%)</span></dd>" +
        "</dl>" +
        (data.sources_checked && data.sources_checked.length
          ? "<p class=\"sources-note\">Checked " + data.sources_checked.length + " source(s).</p>"
          : "");
      resultEl.classList.remove("hidden");
    } else {
      errorEl.textContent = data.error || "No person found for this company and designation.";
      errorEl.classList.remove("hidden");
    }
  }

  function showError(msg) {
    hideAll();
    submitBtn.disabled = false;
    errorEl.textContent = msg || "Something went wrong. Please try again.";
    errorEl.classList.remove("hidden");
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, "&quot;");
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const company = companyInput.value.trim();
    const designation = designationInput.value.trim();
    if (!company || !designation) return;

    showLoading();
    fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company: company, designation: designation }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (res.ok) {
            showResult(data);
          } else {
            showResult(data);
          }
        });
      })
      .catch(function () {
        showError("Network error. Is the server running on port 5000?");
      });
  });
})();
