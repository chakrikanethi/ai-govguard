// State Variables
let documentsProcessed = 0;
let flaggedCount = 0;
let totalSavings = 0;

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const btnSelect = document.querySelector('.btn-select');
const elProcessed = document.getElementById('stats-processed');
const elFlagged = document.getElementById('stats-flagged');
const elSavings = document.getElementById('stats-savings');
const analysisRows = document.getElementById('analysis-rows');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    updateStatsUI();
});

// --- Event Listeners ---

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary)';
    dropZone.style.backgroundColor = '#eff6ff';
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#cbd5e1';
    dropZone.style.backgroundColor = '#f8fafc';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    resetDropZone();
    if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
    }
});

btnSelect.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        handleFiles(fileInput.files);
    }
});

function resetDropZone() {
    dropZone.style.borderColor = '#cbd5e1';
    dropZone.style.backgroundColor = '#f8fafc';
}

// --- Core Logic ---

async function handleFiles(files) {
    for (const file of Array.from(files)) {
        // 1. Prepare Data
        // For JSON files, we read the content. For images/PDFs, we simulate extraction.
        let invoiceData = await parseFile(file);

        // 2. Send to "Agent" (Simulation)
        // This is the functional call to the 'antigravity agent' logic
        const analysisResult = await govguard_fraud_agent(invoiceData);

        // 3. Update State & UI
        updateDashboard(file, invoiceData, analysisResult);
    }
}

async function parseFile(file) {
    if (file.type === 'application/json') {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(JSON.parse(e.target.result));
            reader.readAsText(file);
        });
    } else {
        // Mock data for non-JSON files (Simulating OCR extraction)
        return {
            invoice_id: "INV-" + Math.floor(Math.random() * 10000),
            amount: Math.floor(Math.random() * 80000) + 1000,
            department: Math.random() > 0.5 ? "Public Works" : "IT Services",
            date: new Date().toISOString().split('T')[0],
            vendor: "Acme Corp",
            previous_transactions: [] // Simplified for demo
        };
    }
}

/**
 * AI-GovGuard Fraud Auditor Agent Logic
 * Implements the rules defined in Step 17.
 */
async function govguard_fraud_agent(invoice) {
    // Simulate network delay
    await new Promise(r => setTimeout(r, 600));

    const flags = [];
    const amount = invoice.amount || 0;
    const vendor = invoice.vendor || "Unknown";
    const date = new Date(invoice.date || Date.now());
    const dept = invoice.department || "Unknown";
    const history = invoice.previous_transactions || [];

    // --- RULE EXECUTION ---

    // 1. High Value check
    if (amount > 50000) {
        flags.push("High Value (> $50k)");
    }

    // 2. Round Amount check
    if (amount % 1000 === 0 && amount > 0) {
        flags.push("Round Amount detected");
    }

    // 3. Duplicate History check
    const isDuplicate = history.some(tx => Math.abs(tx.amount - amount) < 0.01);
    if (isDuplicate) {
        flags.push("Potential Duplicate Transaction");
    }

    // 4. High Risk Department check
    if (['Public Works', 'Infrastructure'].includes(dept)) {
        flags.push("High Risk Department");
    }

    // 5. Old Invoice check
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
    if (date < oneYearAgo) {
        flags.push("Invoice > 1 Year Old");
    }

    // 6. Vendor Frequency (Simplified simulation)
    if (amount > 10000 && vendor === "Suspicious Inc") {
        flags.push("Frequent High-Value Vendor");
    }

    // --- DECISION LOGIC ---
    let status = "Clean";
    if (flags.length >= 2) {
        status = "Review Required";
    }

    // --- ESTIMATED SAVINGS ---
    let savings = 0;
    if (status === "Review Required") {
        savings = amount;
    }

    // Structuring the "JSON response"
    return {
        status: status,
        fraud_flags: flags,
        estimated_savings: savings
    };
}

// --- UI Update Logic ---

function updateDashboard(file, invoice, result) {
    // Update Global Counters
    documentsProcessed++;
    if (result.status === "Review Required") {
        flaggedCount++;
        totalSavings += result.estimated_savings;
    }

    // Update Stats UI
    elProcessed.textContent = documentsProcessed;
    elFlagged.textContent = flaggedCount;
    elSavings.textContent = formatCurrency(totalSavings);

    // Update Table
    addInvoiceRow(file, invoice, result);
}

function addInvoiceRow(file, invoice, result) {
    const emptyState = document.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const tr = document.createElement('tr');
    tr.style.animation = "fadeIn 0.5s ease";

    const isClean = result.status === "Clean";
    const badgeClass = isClean ? "badge-clean" : "badge-review";

    // Format flags as tags
    const flagsHtml = result.fraud_flags.length > 0
        ? result.fraud_flags.map(flag => `<span style="display:inline-block; font-size:0.7em; background:#f3f4f6; color:#4b5563; padding:2px 6px; border-radius:4px; margin-right:4px;">${flag}</span>`).join('')
        : '<span style="color:#9ca3af; font-style:italic;">None</span>';

    tr.innerHTML = `
        <td style="font-family:monospace; font-weight:600;">${invoice.invoice_id || 'UNKNOWN'}</td>
        <td>
            <div style="font-weight:500;">${invoice.vendor || 'Unknown'}</div>
            <div style="font-size:0.75em; color:var(--text-secondary);">${file.name}</div>
        </td>
        <td>${invoice.date || '-'}</td>
        <td style="font-weight:600;">${formatCurrency(invoice.amount)}</td>
        <td><span class="badge ${badgeClass}">${result.status}</span></td>
        <td>${flagsHtml}</td>
    `;

    analysisRows.insertBefore(tr, analysisRows.firstChild);
}

function formatCurrency(num) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(num);
}

// Add simple animation styles dynamically
const styleRequest = document.createElement('style');
styleRequest.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(styleRequest);
