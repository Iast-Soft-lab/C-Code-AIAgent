const elements = {
    serverIndicator: document.getElementById("server-indicator"),
    serverStatus: document.getElementById("server-status"),

    fileModeButton: document.getElementById("file-mode-button"),
    codeModeButton: document.getElementById("code-mode-button"),
    fileInputPanel: document.getElementById("file-input-panel"),
    codeInputPanel: document.getElementById("code-input-panel"),

    dropZone: document.getElementById("drop-zone"),
    fileInput: document.getElementById("file-input"),
    fileTypeLabel: document.getElementById("file-type-label"),
    uploadHint: document.getElementById("upload-hint"),

    selectedFile: document.getElementById("selected-file"),
    selectedFileName: document.getElementById("selected-file-name"),
    selectedFileSize: document.getElementById("selected-file-size"),
    removeFile: document.getElementById("remove-file"),

    codeEditor: document.getElementById("code-editor"),
    codeFilenameLabel: document.getElementById("code-filename-label"),
    codeCharacterCount: document.getElementById("code-character-count"),
    codeSizeStatus: document.getElementById("code-size-status"),

    analyzeButton: document.getElementById("analyze-button"),
    uploadStatus: document.getElementById("upload-status"),
    errorBanner: document.getElementById("error-banner"),

    resultsSection: document.getElementById("results-section"),
    reportFileName: document.getElementById("report-file-name"),
    reportStatus: document.getElementById("report-status"),
    reportId: document.getElementById("report-id"),
    downloadButton: document.getElementById("download-button"),

    totalFindings: document.getElementById("total-findings"),
    programmingDefects: document.getElementById("programming-defects"),
    qualityFindings: document.getElementById("quality-findings"),
    misraFindings: document.getElementById("misra-findings"),
    uniqueMisraRules: document.getElementById("unique-misra-rules"),

    searchInput: document.getElementById("search-input"),
    filterButtons: document.querySelectorAll(".filter-button"),
    findingsContainer: document.getElementById("findings-container"),
    visibleCount: document.getElementById("visible-count"),
    emptyFindings: document.getElementById("empty-findings"),

    toolErrors: document.getElementById("tool-errors"),
    toolErrorsContainer: document.getElementById(
        "tool-errors-container"
    )
};


let apiConfig = null;
let selectedFile = null;
let currentReport = null;
let currentInputMode = "file";
let activeFilter = "all";


function createElement(tag, className, text) {

    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined && text !== null) {
        element.textContent = String(text);
    }

    return element;
}


function formatBytes(bytes) {

    if (bytes < 1024) {
        return `${bytes} bytes`;
    }

    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}


function showError(message) {

    elements.errorBanner.textContent = message;
    elements.errorBanner.classList.remove("hidden");
}


function clearError() {

    elements.errorBanner.textContent = "";
    elements.errorBanner.classList.add("hidden");
}


function setServerStatus(online) {

    elements.serverIndicator.classList.toggle("online", online);
    elements.serverIndicator.classList.toggle("offline", !online);

    elements.serverStatus.textContent = online
        ? "Backend connected"
        : "Backend unavailable";
}


async function initializeApplication() {

    try {

        const response = await fetch("/api/ui-config");

        if (!response.ok) {
            throw new Error("Could not load frontend configuration.");
        }

        apiConfig = await response.json();

        const extensions = apiConfig.allowed_extensions || [];

        elements.fileInput.accept = extensions.join(",");
        elements.fileTypeLabel.textContent = extensions.join(", ");

        elements.uploadHint.textContent =
            `Allowed: ${extensions.join(", ")} · Maximum size: ` +
            formatBytes(apiConfig.max_file_size_bytes);

        elements.codeFilenameLabel.textContent =
            `Report filename: ${apiConfig.pasted_code_filename}`;

        const healthResponse = await fetch(apiConfig.health_route);

        if (!healthResponse.ok) {
            throw new Error("Backend health check failed.");
        }

        setServerStatus(true);
        updateAnalyzeButtonState();

    } catch (error) {

        setServerStatus(false);
        showError(error.message);

        elements.uploadStatus.textContent =
            "The application could not connect to the backend.";
    }
}


function switchInputMode(mode) {

    currentInputMode = mode;

    const fileMode = mode === "file";

    elements.fileInputPanel.classList.toggle("hidden", !fileMode);
    elements.codeInputPanel.classList.toggle("hidden", fileMode);

    elements.fileModeButton.classList.toggle("active", fileMode);
    elements.codeModeButton.classList.toggle("active", !fileMode);

    elements.fileModeButton.setAttribute(
        "aria-selected",
        String(fileMode)
    );

    elements.codeModeButton.setAttribute(
        "aria-selected",
        String(!fileMode)
    );

    elements.analyzeButton.textContent = fileMode
        ? "Analyze C file"
        : "Analyze pasted code";

    elements.uploadStatus.textContent = fileMode
        ? "Select a C file to continue."
        : "Paste your C source code to continue.";

    clearError();
    updateAnalyzeButtonState();
}


function validateSelectedFile(file) {

    if (!apiConfig) {
        showError("Application configuration is not available.");
        return false;
    }

    const lowerName = file.name.toLowerCase();

    const allowed = apiConfig.allowed_extensions.some(
        extension => lowerName.endsWith(extension.toLowerCase())
    );

    if (!allowed) {
        showError(
            `Unsupported file type. Allowed: ${
                apiConfig.allowed_extensions.join(", ")
            }`
        );

        return false;
    }

    if (file.size > apiConfig.max_file_size_bytes) {
        showError(
            `File is too large. Maximum allowed size is ${
                formatBytes(apiConfig.max_file_size_bytes)
            }.`
        );

        return false;
    }

    if (file.size === 0) {
        showError("The selected file is empty.");
        return false;
    }

    return true;
}


function selectFile(file) {

    clearError();

    if (!file || !validateSelectedFile(file)) {
        return;
    }

    selectedFile = file;

    elements.selectedFileName.textContent = file.name;
    elements.selectedFileSize.textContent = formatBytes(file.size);

    elements.selectedFile.classList.remove("hidden");
    elements.dropZone.classList.add("hidden");

    elements.uploadStatus.textContent = "File ready for analysis.";

    updateAnalyzeButtonState();
}


function clearSelectedFile() {

    selectedFile = null;
    elements.fileInput.value = "";

    elements.selectedFile.classList.add("hidden");
    elements.dropZone.classList.remove("hidden");

    elements.uploadStatus.textContent = "Select a file to continue.";

    updateAnalyzeButtonState();
}


function getPastedCodeSize() {

    return new TextEncoder().encode(
        elements.codeEditor.value
    ).length;
}


function updateCodeEditorStatus() {

    const code = elements.codeEditor.value;
    const bytes = getPastedCodeSize();

    elements.codeCharacterCount.textContent =
        `${code.length} characters · ${formatBytes(bytes)}`;

    if (!apiConfig) {
        elements.codeSizeStatus.textContent =
            "Loading configuration...";
        return;
    }

    if (bytes > apiConfig.max_file_size_bytes) {
        elements.codeSizeStatus.textContent =
            "Code exceeds the configured size limit.";
        elements.codeSizeStatus.classList.add("limit-exceeded");
    } else {
        elements.codeSizeStatus.textContent =
            "Ready for analysis.";
        elements.codeSizeStatus.classList.remove("limit-exceeded");
    }

    updateAnalyzeButtonState();
}


function updateAnalyzeButtonState() {

    if (!apiConfig) {
        elements.analyzeButton.disabled = true;
        return;
    }

    if (currentInputMode === "file") {
        elements.analyzeButton.disabled = !selectedFile;
        return;
    }

    const code = elements.codeEditor.value.trim();

    const validCode = (
        code.length > 0 &&
        getPastedCodeSize() <= apiConfig.max_file_size_bytes
    );

    elements.analyzeButton.disabled = !validCode;
}


function renderDiagnosticDetails(container, finding) {

    const details = createElement("details", "diagnostic-details");

    details.appendChild(
        createElement("summary", "", "Inspect diagnostic evidence")
    );

    const diagnosticContent = {
        messages: finding.messages || [],
        tool_diagnostics: finding.tool_diagnostics || []
    };

    details.appendChild(
        createElement(
            "pre",
            "",
            JSON.stringify(diagnosticContent, null, 2)
        )
    );

    container.appendChild(details);
}


function renderFinding(finding) {

    const card = createElement("article", "finding-card");

    const top = createElement("div", "finding-top");

    top.appendChild(
        createElement("span", "finding-id", finding.finding_id)
    );

    const severity = String(
        finding.severity || "unknown"
    ).toLowerCase();

    const allowedSeverities = [
        "error",
        "warning",
        "style",
        "information"
    ];

    const severityClass = allowedSeverities.includes(severity)
        ? severity
        : "unknown";

    top.appendChild(
        createElement(
            "span",
            `severity severity-${severityClass}`,
            severity
        )
    );

    card.appendChild(top);

    card.appendChild(
        createElement(
            "h3",
            "",
            finding.issue_type || "Unclassified issue"
        )
    );

    card.appendChild(
        createElement(
            "p",
            "",
            finding.message || "No message provided."
        )
    );

    const meta = createElement("div", "finding-meta");

    meta.appendChild(
        createElement(
            "span",
            "",
            `${finding.file || "Unknown file"} : ${finding.line ?? "Unknown line"}`
        )
    );

    meta.appendChild(
        createElement(
            "span",
            "",
            finding.category || "Uncategorized"
        )
    );

    card.appendChild(meta);

    const badges = createElement("div", "badge-row");

    for (const tool of finding.detected_by || []) {
        badges.appendChild(
            createElement("span", "finding-badge", tool)
        );
    }

    if (finding.misra_rule_id) {
        badges.appendChild(
            createElement("span", "finding-badge", finding.misra_rule_id)
        );
    }

    if (finding.cwe) {
        badges.appendChild(
            createElement("span", "finding-badge", `CWE-${finding.cwe}`)
        );
    }

    card.appendChild(badges);

    renderDiagnosticDetails(card, finding);

    return card;
}


/*
 * Group MISRA occurrences by source file and rule ID.
 *
 * Each source location remains a separate finding in the JSON report.
 * Grouping only changes how the frontend displays those occurrences.
 */
function groupFindingsForDisplay(findings) {

    const displayItems = [];
    const misraGroups = new Map();

    for (const finding of findings) {

        if (finding.analysis_type !== "misra") {

            displayItems.push({
                type: "single",
                finding
            });

            continue;
        }

        const groupKey = JSON.stringify([
            finding.file,
            finding.misra_rule_id || finding.issue_type
        ]);

        if (!misraGroups.has(groupKey)) {

            const group = {
                type: "misra_group",
                file: finding.file,
                ruleId: finding.misra_rule_id || "MISRA rule",
                findings: []
            };

            misraGroups.set(groupKey, group);
            displayItems.push(group);
        }

        misraGroups.get(groupKey).findings.push(finding);
    }

    return displayItems;
}


function renderMisraGroup(group) {

    const card = createElement(
        "article",
        "finding-card misra-group-card"
    );

    const top = createElement("div", "finding-top");

    top.appendChild(
        createElement("span", "finding-id", group.ruleId)
    );

    top.appendChild(
        createElement(
            "span",
            "severity severity-style",
            `${group.findings.length} occurrence(s)`
        )
    );

    card.appendChild(top);

    card.appendChild(
        createElement("h3", "", "MISRA Rule Violation")
    );

    card.appendChild(
        createElement(
            "p",
            "",
            `This rule was reported at ${group.findings.length} distinct source location(s).`
        )
    );

    const locationList = createElement("div", "misra-occurrences");

    for (const finding of group.findings) {

        const occurrence = createElement(
            "div",
            "misra-occurrence"
        );

        const locationHeading = createElement(
            "div",
            "misra-location-heading"
        );

        const locationText = [
            finding.finding_id,
            `Line ${finding.line ?? "unknown"}`,
            finding.column !== null && finding.column !== undefined
                ? `Column ${finding.column}`
                : null
        ].filter(Boolean).join(" · ");

        locationHeading.appendChild(
            createElement("strong", "", locationText)
        );

        occurrence.appendChild(locationHeading);

        occurrence.appendChild(
            createElement(
                "p",
                "misra-occurrence-message",
                finding.message || "MISRA violation reported."
            )
        );

        renderDiagnosticDetails(occurrence, finding);

        locationList.appendChild(occurrence);
    }

    card.appendChild(locationList);

    const badges = createElement("div", "badge-row");

    badges.appendChild(
        createElement(
            "span",
            "finding-badge",
            "Cppcheck MISRA Addon"
        )
    );

    badges.appendChild(
        createElement(
            "span",
            "finding-badge",
            `${group.findings.length} source location(s)`
        )
    );

    card.appendChild(badges);

    return card;
}


function renderFindings() {

    if (!currentReport) {
        return;
    }

    const searchText = elements.searchInput.value
        .trim()
        .toLowerCase();

    const findings = currentReport.findings || [];

    const filteredFindings = findings.filter(finding => {

        const matchesFilter = (
            activeFilter === "all" ||
            finding.analysis_type === activeFilter
        );

        const searchableText = [
            finding.finding_id,
            finding.issue_type,
            finding.category,
            finding.severity,
            finding.message,
            finding.file,
            finding.line,
            finding.column,
            finding.misra_rule_id,
            ...(finding.detected_by || [])
        ].join(" ").toLowerCase();

        return matchesFilter && searchableText.includes(searchText);
    });

    const displayItems = groupFindingsForDisplay(filteredFindings);

    elements.findingsContainer.replaceChildren();

    for (const item of displayItems) {

        if (item.type === "misra_group") {
            elements.findingsContainer.appendChild(
                renderMisraGroup(item)
            );
        } else {
            elements.findingsContainer.appendChild(
                renderFinding(item.finding)
            );
        }
    }

    elements.visibleCount.textContent =
        `${filteredFindings.length} occurrences across ` +
        `${displayItems.length} displayed card(s)`;

    elements.emptyFindings.classList.toggle(
        "hidden",
        filteredFindings.length > 0
    );
}


function renderToolErrors(errors) {

    elements.toolErrorsContainer.replaceChildren();

    if (!errors || errors.length === 0) {
        elements.toolErrors.classList.add("hidden");
        return;
    }

    elements.toolErrors.classList.remove("hidden");

    for (const item of errors) {

        const message = `${item.tool}: ${item.error}`;

        elements.toolErrorsContainer.appendChild(
            createElement("p", "tool-error-item", message)
        );
    }
}


function renderReport(report) {

    currentReport = report;
    activeFilter = "all";

    elements.reportFileName.textContent =
        `Source: ${report.file_name}`;

    elements.reportStatus.textContent =
        `Status: ${report.analysis_status}`;

    elements.reportId.textContent =
        `Report ID: ${report.report_id}`;

    elements.totalFindings.textContent =
        report.summary.total_findings;

    elements.programmingDefects.textContent =
        report.summary.programming_defects;

    elements.qualityFindings.textContent =
        report.summary.code_quality_findings;

    elements.misraFindings.textContent =
        report.summary.misra_violations;

    elements.uniqueMisraRules.textContent =
        report.summary.misra_unique_rules;

    elements.downloadButton.href =
        apiConfig.download_route_template.replace(
            "{report_id}",
            encodeURIComponent(report.report_id)
        );

    elements.searchInput.value = "";

    elements.filterButtons.forEach(button => {
        button.classList.toggle(
            "active",
            button.dataset.filter === "all"
        );
    });

    renderFindings();
    renderToolErrors(report.tool_errors);

    elements.resultsSection.classList.remove("hidden");

    elements.resultsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


async function analyzeSelectedInput() {

    if (!apiConfig) {
        return;
    }

    const formData = new FormData();

    if (currentInputMode === "file") {

        if (!selectedFile) {
            showError("Select a C file first.");
            return;
        }

        formData.append("file", selectedFile);

    } else {

        const code = elements.codeEditor.value;

        if (!code.trim()) {
            showError("Paste your C source code first.");
            return;
        }

        if (getPastedCodeSize() > apiConfig.max_file_size_bytes) {
            showError("Pasted code exceeds the configured size limit.");
            return;
        }

        formData.append("code", code);
    }

    clearError();

    elements.analyzeButton.disabled = true;
    elements.analyzeButton.textContent = "Analyzing...";

    elements.uploadStatus.textContent =
        "Running Clang, Cppcheck and MISRA analysis...";

    try {

        const response = await fetch(apiConfig.analyze_route, {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Analysis request failed."
            );
        }

        renderReport(result);

        elements.uploadStatus.textContent =
            "Analysis completed successfully.";

    } catch (error) {

        showError(error.message);

        elements.uploadStatus.textContent =
            "Analysis could not be completed.";

    } finally {

        elements.analyzeButton.textContent =
            currentInputMode === "file"
                ? "Analyze C file"
                : "Analyze pasted code";

        updateAnalyzeButtonState();
    }
}


elements.fileModeButton.addEventListener(
    "click",
    () => switchInputMode("file")
);

elements.codeModeButton.addEventListener(
    "click",
    () => switchInputMode("code")
);


elements.fileInput.addEventListener("change", event => {

    const file = event.target.files[0];

    if (file) {
        selectFile(file);
    }
});


elements.removeFile.addEventListener(
    "click",
    clearSelectedFile
);


elements.codeEditor.addEventListener("input", () => {
    clearError();
    updateCodeEditorStatus();
});


elements.analyzeButton.addEventListener(
    "click",
    analyzeSelectedInput
);


elements.searchInput.addEventListener(
    "input",
    renderFindings
);


elements.filterButtons.forEach(button => {

    button.addEventListener("click", () => {

        activeFilter = button.dataset.filter;

        elements.filterButtons.forEach(item => {
            item.classList.toggle("active", item === button);
        });

        renderFindings();
    });
});


elements.dropZone.addEventListener("dragover", event => {
    event.preventDefault();
    elements.dropZone.classList.add("dragging");
});


elements.dropZone.addEventListener("dragleave", () => {
    elements.dropZone.classList.remove("dragging");
});


elements.dropZone.addEventListener("drop", event => {

    event.preventDefault();

    elements.dropZone.classList.remove("dragging");

    const file = event.dataTransfer.files[0];

    if (file) {
        selectFile(file);
    }
});


initializeApplication();
