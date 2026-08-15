// LexAgents Frontend Client Logic
document.addEventListener("DOMContentLoaded", () => {
    // Nav elements
    const tabChat = document.getElementById("tab-chat");
    const tabEval = document.getElementById("tab-eval");
    const paneChat = document.getElementById("pane-chat");
    const paneEval = document.getElementById("pane-eval");
    
    // Ingestion Upload
    const uploadForm = document.getElementById("upload-form");
    const fileInput = document.getElementById("file-input");
    const uploadStatus = document.getElementById("upload-status");

    // Research Interface
    const queryInput = document.getElementById("query-input");
    const webToggle = document.getElementById("web-toggle");
    const runBtn = document.getElementById("run-btn");
    const researchLoader = document.getElementById("research-loader");
    const loaderStatus = document.getElementById("loader-status");
    const researchResults = document.getElementById("research-results");
    
    // Research result panels
    const resIterations = document.getElementById("res-iterations");
    const resLatency = document.getElementById("res-latency");
    const resStatus = document.getElementById("res-status");
    const resAnswer = document.getElementById("res-answer");
    const resVerification = document.getElementById("res-verification");
    const resCitations = document.getElementById("res-citations");
    const resTrace = document.getElementById("res-trace");

    // Evaluation Interface
    const runEvalBtn = document.getElementById("run-eval-btn");
    const evalLoader = document.getElementById("eval-loader");
    const evalResultsContainer = document.getElementById("eval-results-container");
    const evalMetricsBody = document.getElementById("eval-metrics-body");
    const evalChartImg = document.getElementById("eval-chart-img");
    const historicalEvalsList = document.getElementById("historical-evals-list");

    let currentSessionId = null;

    // --- 1. Tab Navigation ---
    tabChat.addEventListener("click", () => {
        tabChat.classList.add("active");
        tabEval.classList.remove("active");
        paneChat.classList.add("active");
        paneEval.classList.remove("active");
    });

    tabEval.addEventListener("click", () => {
        tabEval.classList.add("active");
        tabChat.classList.remove("active");
        paneEval.classList.add("active");
        paneChat.classList.remove("active");
        loadHistoricalEvaluations();
    });

    // --- 2. Ingestion Upload form ---
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;

        uploadStatus.className = "status-msg";
        uploadStatus.textContent = "Uploading and indexing document...";
        uploadStatus.style.display = "block";

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/documents/upload", {
                method: "POST",
                body: formData
            });

            const data = await res.json();
            if (res.ok) {
                uploadStatus.classList.add("success");
                uploadStatus.textContent = `Ingestion complete! ${data.filename} split into ${data.chunks_ingested} clauses.`;
                fileInput.value = "";
            } else {
                uploadStatus.classList.add("error");
                uploadStatus.textContent = `Ingestion failed: ${data.detail || "Unknown error"}`;
            }
        } catch (error) {
            uploadStatus.classList.add("error");
            uploadStatus.textContent = `Network error during upload: ${error.message}`;
        }
    });

    // --- 3. Run Research Agent Loop ---
    runBtn.addEventListener("click", async () => {
        const query = queryInput.value.trim();
        if (!query) return;

        // Reset UI
        researchResults.classList.add("hidden");
        researchLoader.classList.remove("hidden");
        runBtn.disabled = true;
        
        // Progress messages
        const progressSteps = [
            "Coordinator decomposing query and planning specialized agent tasks...",
            "Invoking Case Law and Statute retrieval agents in parallel...",
            "Aggregating evidence, synthesizing draft answer and footnoting sources...",
            "Verification Agent extracting claims and validating factual alignment...",
            "Reflection loop evaluating claim support correctness..."
        ];
        
        let stepIdx = 0;
        loaderStatus.textContent = progressSteps[0];
        const progressInterval = setInterval(() => {
            stepIdx = (stepIdx + 1) % progressSteps.length;
            loaderStatus.textContent = progressSteps[stepIdx];
        }, 3000);

        try {
            const payload = {
                query: query,
                session_id: currentSessionId,
                use_web: webToggle.checked
            };

            const res = await fetch("/api/research", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonPayload = JSON.stringify(payload)
            });

            clearInterval(progressInterval);
            researchLoader.classList.add("hidden");
            runBtn.disabled = false;

            const data = await res.json();
            if (res.ok) {
                renderResearchResults(data);
            } else {
                alert(`Research query failed: ${data.detail || "Server error"}`);
            }
        } catch (error) {
            clearInterval(progressInterval);
            researchLoader.classList.add("hidden");
            runBtn.disabled = false;
            alert(`Network error: ${error.message}`);
        }
    });

    function renderResearchResults(data) {
        // Track session ID for follow-ups
        currentSessionId = data.session_id;

        // Show pane
        researchResults.classList.remove("hidden");

        // 1. Fill metrics cards
        resIterations.textContent = data.iterations;
        resLatency.textContent = `${data.latency ? data.latency.toFixed(2) : "0.00"}s`;
        
        // Determine system status based on unsupported claims
        const unsupportedCount = data.verification_results.filter(v => !v.supported).length;
        if (unsupportedCount === 0) {
            resStatus.textContent = "Verified";
            resStatus.className = "stat-value status-good";
        } else {
            resStatus.textContent = `${unsupportedCount} Claim(s) Unsupported`;
            resStatus.className = "stat-value status-warn";
        }

        // 2. Render Answer with interactive citation highlights
        let answerHTML = data.answer;
        // Parse citations like [1], [2] to span badges
        answerHTML = answerHTML.replace(/\[(\d+)\]/g, (match, num) => {
            return `<span class="citation-link" data-citation-num="${num}">${num}</span>`;
        });
        // Replace newlines with <br> or paragraphs
        resAnswer.innerHTML = answerHTML.split("\n\n").map(para => `<p style="margin-bottom:0.75rem">${para}</p>`).join("");

        // Add interactive highlights to citation links
        setTimeout(() => {
            document.querySelectorAll(".citation-link").forEach(link => {
                link.addEventListener("click", () => {
                    const num = link.getAttribute("data-citation-num");
                    const targetCard = document.getElementById(`cite-card-${num}`);
                    if (targetCard) {
                        targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
                        targetCard.style.backgroundColor = "var(--bg-hover)";
                        setTimeout(() => {
                            targetCard.style.backgroundColor = "var(--bg-main)";
                        }, 2000);
                    }
                });
            });
        }, 100);

        // 3. Render Claims Verification list
        resVerification.innerHTML = "";
        data.verification_results.forEach(v => {
            const verCard = document.createElement("div");
            verCard.className = `verification-item ${v.supported ? 'verified' : 'unsupported'}`;
            
            const claimText = document.createElement("div");
            claimText.className = "ver-claim";
            claimText.textContent = v.claim;
            verCard.appendChild(claimText);

            const badge = document.createElement("span");
            badge.className = `ver-badge ${v.supported ? 'verified' : 'unsupported'}`;
            badge.textContent = v.supported ? "Verified" : "Unsupported / Ambiguous";
            verCard.appendChild(badge);

            if (v.issues && v.issues.length > 0) {
                const issuesDiv = document.createElement("div");
                issuesDiv.className = "ver-issues";
                issuesDiv.textContent = `Discrepancy: ${v.issues.join(", ")}`;
                verCard.appendChild(issuesDiv);
            }

            resVerification.appendChild(verCard);
        });

        // 4. Render Citations evidence cards
        resCitations.innerHTML = "";
        data.citations.forEach((c, idx) => {
            const citeCard = document.createElement("div");
            citeCard.className = "citation-item";
            citeCard.id = `cite-card-${idx + 1}`;

            const header = document.createElement("div");
            header.className = "cite-header";
            
            const title = document.createElement("span");
            title.className = "cite-title";
            title.textContent = `[${idx + 1}] ${c.source}`;
            header.appendChild(title);

            const typeBadge = document.createElement("span");
            typeBadge.className = "cite-type";
            typeBadge.textContent = c.doc_type;
            header.appendChild(typeBadge);
            
            citeCard.appendChild(header);

            const bodyText = document.createElement("div");
            bodyText.className = "cite-text";
            bodyText.textContent = c.text;
            citeCard.appendChild(bodyText);

            resCitations.appendChild(citeCard);
        });

        // 5. Render Trace history timeline
        resTrace.innerHTML = "";
        data.trace.forEach(step => {
            const node = document.createElement("div");
            node.className = "trace-node";

            const titleNode = document.createElement("div");
            titleNode.className = "trace-title-node";
            titleNode.textContent = step.step_name;
            node.appendChild(titleNode);

            const timeNode = document.createElement("div");
            timeNode.className = "trace-time";
            // Clean time display
            const d = new Date(step.timestamp);
            timeNode.textContent = d.toLocaleTimeString();
            node.appendChild(timeNode);

            const payloadNode = document.createElement("pre");
            payloadNode.className = "trace-payload";
            payloadNode.textContent = JSON.stringify(step.payload, null, 2);
            node.appendChild(payloadNode);

            resTrace.appendChild(node);
        });
    }

    // --- 4. Run Evaluation ---
    runEvalBtn.addEventListener("click", async () => {
        evalResultsContainer.classList.add("hidden");
        evalLoader.classList.remove("hidden");
        runEvalBtn.disabled = true;

        try {
            const res = await fetch("/api/evaluate", { method: "POST" });
            const data = await res.json();
            
            evalLoader.classList.add("hidden");
            runEvalBtn.disabled = false;

            if (res.ok) {
                renderEvaluationResults(data.results);
                loadHistoricalEvaluations();
            } else {
                alert(`Evaluation run failed: ${data.detail || "Unknown error"}`);
            }
        } catch (error) {
            evalLoader.classList.add("hidden");
            runEvalBtn.disabled = false;
            alert(`Network error during evaluation: ${error.message}`);
        }
    });

    function renderEvaluationResults(results) {
        evalResultsContainer.classList.remove("hidden");
        evalMetricsBody.innerHTML = "";
        
        // Compute averages to render
        const averages = computeMacroAverages(results);
        const systems = ["Baseline_A", "Baseline_B", "System_C", "System_D"];
        const systemLabels = {
            "Baseline_A": "Baseline A: Conventional Vector RAG",
            "Baseline_B": "Baseline B: Multi-Agent RAG",
            "System_C": "System C: Multi-Agent + Verification",
            "System_D": "System D: Full Proposed System (Iterative)"
        };

        systems.forEach(sys => {
            const metrics = averages[sys];
            const tr = document.createElement("tr");
            
            tr.innerHTML = `
                <td><strong>${systemLabels[sys]}</strong></td>
                <td>${metrics.avg_latency.toFixed(2)}s</td>
                <td>${metrics.avg_iterations.toFixed(1)}</td>
                <td>${(metrics.retrieval_precision * 100).toFixed(1)}%</td>
                <td>${(metrics.retrieval_recall * 100).toFixed(1)}%</td>
                <td>${(metrics.citation_precision * 100).toFixed(1)}%</td>
                <td>${(metrics.citation_recall * 100).toFixed(1)}%</td>
                <td><span class="${metrics.unsupported_claim_rate > 0.1 ? 'badge-danger' : 'badge-success'}">${(metrics.unsupported_claim_rate * 100).toFixed(1)}%</span></td>
            `;
            
            evalMetricsBody.appendChild(tr);
        });

        // Set comparison chart image source with anti-caching timestamp
        evalChartImg.src = `/experiments/results/comparison_chart.png?t=${new Date().getTime()}`;
    }

    function computeMacroAverages(results) {
        const avgs = {};
        const systems = ["Baseline_A", "Baseline_B", "System_C", "System_D"];
        const count = results.length;

        systems.forEach(sys => {
            let sumLatency = 0, sumIterations = 0, sumRetP = 0, sumRetR = 0, sumCitP = 0, sumCitR = 0, sumUnsup = 0;
            
            results.forEach(r => {
                const s = r[sys];
                sumLatency += s.latency;
                sumIterations += s.iterations;
                sumRetP += s.retrieval_precision;
                sumRetR += s.retrieval_recall;
                sumCitP += s.citation_precision;
                sumCitR += s.citation_recall;
                sumUnsup += s.unsupported_claim_rate;
            });

            avgs[sys] = {
                avg_latency: sumLatency / count,
                avg_iterations: sumIterations / count,
                retrieval_precision: sumRetP / count,
                retrieval_recall: sumRetR / count,
                citation_precision: sumCitP / count,
                citation_recall: sumCitR / count,
                unsupported_claim_rate: sumUnsup / count
            };
        });
        return avgs;
    }

    async function loadHistoricalEvaluations() {
        try {
            const res = await fetch("/api/evaluation/results");
            if (res.ok) {
                const data = await res.json();
                historicalEvalsList.innerHTML = "";
                
                if (data.length === 0) {
                    historicalEvalsList.innerHTML = "<p class='section-desc'>No past evaluation runs recorded yet.</p>";
                    return;
                }

                data.forEach(run => {
                    const item = document.createElement("div");
                    item.className = "eval-history-item";
                    
                    const d = new Date(run.run_timestamp);
                    const formattedDate = d.toLocaleString();

                    // Retrieve System D stats as representational of the run
                    const dStats = run.metrics.System_D || {};
                    
                    item.innerHTML = `
                        <div>
                            <strong>Run ID: ${run.eval_id}</strong>
                            <div style="color:var(--text-muted);font-size:0.75rem">${formattedDate}</div>
                        </div>
                        <div style="text-align:right">
                            <div>System D Citation Precision: <strong>${(dStats.citation_precision * 100).toFixed(1)}%</strong></div>
                            <div style="color:var(--text-muted);font-size:0.75rem">Unsupported Claim Rate: ${(dStats.unsupported_claim_rate * 100).toFixed(1)}%</div>
                        </div>
                    `;
                    historicalEvalsList.appendChild(item);
                });
            }
        } catch (error) {
            console.error("Failed to load historical evaluations", error);
        }
    }
});
