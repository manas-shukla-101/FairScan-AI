import React, { useState } from 'react';
import {
  Upload,
  RotateCcw,
  Download,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Sliders,
  Database,
  Layers,
  BarChart3,
  ExternalLink,
  ChevronRight,
  Shield,
  Fingerprint,
  Info,
  ArrowRight,
  Activity,
  Cpu,
  Sparkles,
  Zap,
  Check,
  AlertCircle,
  Eye,
  EyeOff,
  Key,
  Lock,
  SlidersHorizontal,
  ChevronDown
} from 'lucide-react';
import Plot from 'react-plotly.js';
import { FairScanLogo } from './components/FairScanLogo';

const API_BASE = '/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('audit'); // 'audit', 'mitigation', 'report', 'data'
  const [datasetMeta, setDatasetMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);

  // Auto Configured State
  const [autoConfig, setAutoConfig] = useState(null);
  const [showConfigModal, setShowConfigModal] = useState(false);

  // Audit Configuration Values
  const [targetCol, setTargetCol] = useState('');
  const [favorableOutcome, setFavorableOutcome] = useState('');
  const [sensitiveCols, setSensitiveCols] = useState([]);
  const [referenceGroups, setReferenceGroups] = useState({});
  const [predictionCol, setPredictionCol] = useState('');

  // User Custom API Keys State (Persisted in browser localStorage)
  const [groqKey, setGroqKey] = useState(() => localStorage.getItem('fairscan_groq_key') || '');
  const [geminiKey, setGeminiKey] = useState(() => localStorage.getItem('fairscan_gemini_key') || '');
  const [llmProvider, setLlmProvider] = useState(() => localStorage.getItem('fairscan_llm_provider') || 'auto');
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [showGroqKey, setShowGroqKey] = useState(false);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [savedKeyFeedback, setSavedKeyFeedback] = useState(false);

  const saveApiKeys = (newGroq, newGemini, newProvider) => {
    setGroqKey(newGroq);
    setGeminiKey(newGemini);
    setLlmProvider(newProvider);
    localStorage.setItem('fairscan_groq_key', newGroq.trim());
    localStorage.setItem('fairscan_gemini_key', newGemini.trim());
    localStorage.setItem('fairscan_llm_provider', newProvider);
    setSavedKeyFeedback(true);
    setTimeout(() => setSavedKeyFeedback(false), 2000);
  };

  const clearApiKeys = () => {
    setGroqKey('');
    setGeminiKey('');
    setLlmProvider('auto');
    localStorage.removeItem('fairscan_groq_key');
    localStorage.removeItem('fairscan_gemini_key');
    localStorage.removeItem('fairscan_llm_provider');
  };

  const getCustomAuthHeaders = () => {
    const headers = {};
    if (groqKey && groqKey.trim()) headers['x-groq-api-key'] = groqKey.trim();
    if (geminiKey && geminiKey.trim()) headers['x-gemini-api-key'] = geminiKey.trim();
    if (llmProvider) headers['x-llm-provider'] = llmProvider;
    return headers;
  };

  // Results State
  const [profileData, setProfileData] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [findingsData, setFindingsData] = useState(null);
  const [explanationData, setExplanationData] = useState(null);

  // Mitigation State
  const [mitigationCol, setMitigationCol] = useState('');
  const [mitigationRef, setMitigationRef] = useState('');
  const [mitigationResult, setMitigationResult] = useState(null);
  const [mitigationLoading, setMitigationLoading] = useState(false);

  // 1-Click Upload & Auto-Audit
  const handleAutoAuditUpload = async (file) => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    setLoadingStep('Uploading dataset…');
    setErrorMsg(null);

    try {
      setTimeout(() => setLoadingStep('Finding what was measured and who is in the dataset…'), 600);
      setTimeout(() => setLoadingStep('Checking if everyone is treated fairly…'), 1200);
      setTimeout(() => setLoadingStep('Writing simple summary report…'), 1800);

      const resp = await fetch(`${API_BASE}/auto-audit`, {
        method: 'POST',
        body: formData,
        headers: getCustomAuthHeaders(),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Failed to check dataset.');

      setDatasetMeta(data.dataset_metadata);
      setAutoConfig(data.auto_config);
      setTargetCol(data.auto_config.auto_target_col);
      setFavorableOutcome(data.auto_config.auto_favorable_outcome);
      setSensitiveCols(data.auto_config.auto_sensitive_cols);
      setReferenceGroups(data.auto_config.auto_reference_groups);
      setPredictionCol(data.auto_config.auto_prediction_col || '');

      setProfileData(data.profile);
      setAuditData(data.audit_results);
      setFindingsData(data.findings);
      setExplanationData(data.explanation);

      if (data.mitigation) {
        setMitigationResult(data.mitigation);
        setMitigationCol(data.mitigation.sensitive_col);
        setMitigationRef(data.mitigation.reference_group);
      }

      setActiveTab('audit');
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
      setLoadingStep('');
    }
  };

  const handleAutoAuditSample = async (sampleType) => {
    setLoading(true);
    setLoadingStep(`Loading ${sampleType} example and running fairness check…`);
    setErrorMsg(null);

    try {
      const resp = await fetch(`${API_BASE}/auto-audit?sample_name=${sampleType}`, {
        method: 'POST',
        headers: getCustomAuthHeaders(),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Could not test example.');

      setDatasetMeta(data.dataset_metadata);
      setAutoConfig(data.auto_config);
      setTargetCol(data.auto_config.auto_target_col);
      setFavorableOutcome(data.auto_config.auto_favorable_outcome);
      setSensitiveCols(data.auto_config.auto_sensitive_cols);
      setReferenceGroups(data.auto_config.auto_reference_groups);
      setPredictionCol(data.auto_config.auto_prediction_col || '');

      setProfileData(data.profile);
      setAuditData(data.audit_results);
      setFindingsData(data.findings);
      setExplanationData(data.explanation);

      if (data.mitigation) {
        setMitigationResult(data.mitigation);
        setMitigationCol(data.mitigation.sensitive_col);
        setMitigationRef(data.mitigation.reference_group);
      }

      setActiveTab('audit');
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
      setLoadingStep('');
    }
  };

  const handleCustomAuditReRun = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const resp = await fetch(`${API_BASE}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getCustomAuthHeaders() },
        body: JSON.stringify({
          target_col: targetCol,
          favorable_outcome: favorableOutcome,
          sensitive_cols: sensitiveCols,
          reference_groups: referenceGroups,
          prediction_col: predictionCol || null,
          llm_provider: llmProvider,
          groq_api_key: groqKey.trim() || null,
          gemini_api_key: geminiKey.trim() || null,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Re-check failed.');

      setAuditData(data.audit_results);
      setFindingsData(data.findings);
      setProfileData(data.profile);
      setExplanationData(data.explanation);
      setShowConfigModal(false);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      await fetch(`${API_BASE}/reset`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
    setDatasetMeta(null);
    setAutoConfig(null);
    setProfileData(null);
    setAuditData(null);
    setFindingsData(null);
    setExplanationData(null);
    setTargetCol('');
    setFavorableOutcome('');
    setSensitiveCols([]);
    setReferenceGroups({});
    setPredictionCol('');
    setMitigationResult(null);
    setErrorMsg(null);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white flex flex-col font-sans selection:bg-[#facc15] selection:text-black">
      {/* 1. Header */}
      <header className="border-b border-[#1f1f24] bg-[#0e0e12]/95 backdrop-blur-md px-6 py-3.5 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2.5 cursor-pointer" onClick={() => setActiveTab('audit')}>
            <FairScanLogo className="w-8 h-8" />
            <div className="flex items-center space-x-2">
              <span className="text-lg font-bold tracking-tight text-white">FairScan</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#facc15]/10 border border-[#facc15]/30 text-[#facc15] font-semibold">
                FAIRNESS CHECK
              </span>
            </div>
          </div>

          {datasetMeta && (
            <>
              <div className="h-4 w-px bg-[#26262d] hidden md:block"></div>
              <nav className="hidden md:flex items-center space-x-1">
                {[
                  { id: 'audit', label: '1. Results & Fairness Check', icon: BarChart3 },
                  { id: 'mitigation', label: '2. Fix Bias (Balance Data)', icon: Layers },
                  { id: 'report', label: '3. Download Report', icon: FileText },
                  { id: 'data', label: '4. View Raw Data', icon: Database },
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        isActive
                          ? 'bg-white text-black font-bold shadow-sm'
                          : 'text-zinc-400 hover:text-white hover:bg-zinc-900/80'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </nav>
            </>
          )}
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center space-x-2.5">
          {/* Universal API Keys Button */}
          <button
            onClick={() => setShowKeyModal(true)}
            className={`px-3 py-1.5 rounded-lg border text-xs flex items-center space-x-1.5 transition ${
              groqKey || geminiKey
                ? 'border-[#facc15]/50 bg-[#facc15]/10 text-white font-medium hover:bg-[#facc15]/20'
                : 'border-[#272730] hover:bg-[#18181d] text-zinc-300'
            }`}
            title="Configure Groq or Gemini API keys for plain-English explanations"
          >
            <Key className={`w-3.5 h-3.5 ${groqKey || geminiKey ? 'text-[#facc15]' : 'text-zinc-400'}`} />
            <span>API Keys</span>
            {(groqKey || geminiKey) && (
              <span className="w-1.5 h-1.5 rounded-full bg-[#facc15] ml-0.5 animate-pulse" />
            )}
          </button>

          {datasetMeta ? (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowConfigModal(true)}
                className="px-3 py-1.5 rounded-lg border border-[#272730] hover:bg-[#18181d] text-xs text-zinc-300 flex items-center space-x-1.5 transition"
                title="Change detected columns or groups"
              >
                <SlidersHorizontal className="w-3 h-3 text-[#facc15]" />
                <span className="hidden sm:inline">Adjust Settings</span>
              </button>

              <a
                href={`${API_BASE}/report/pdf`}
                download="fairscan_audit_report.pdf"
                className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-[#facc15] hover:bg-[#eab308] text-black flex items-center space-x-1.5 transition shadow-sm"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download PDF Report</span>
              </a>

              <button
                onClick={handleReset}
                title="Test another file"
                className="p-1.5 rounded-lg border border-[#272730] hover:bg-[#18181d] text-zinc-400 hover:text-white transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleAutoAuditSample('hiring')}
                className="px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition"
              >
                Try Job Hiring Example
              </button>
              <button
                onClick={() => handleAutoAuditSample('lending')}
                className="px-3 py-1.5 rounded-lg bg-[#facc15] hover:bg-[#eab308] text-black font-bold text-xs transition"
              >
                Try Loan Approval Example
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Global Error Banner */}
      {errorMsg && (
        <div className="bg-red-950/70 border-b border-red-900/60 px-6 py-2.5 flex items-center justify-between text-xs text-red-200">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-white font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-8">
        {/* ========================================================================= */}
        {/* 1. SIMPLE UPLOAD VIEW                                                     */}
        {/* ========================================================================= */}
        {!datasetMeta && (
          <div className="space-y-10 py-8 max-w-4xl mx-auto">
            <div className="text-center space-y-3">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#facc15]/10 border border-[#facc15]/30 text-[#facc15] text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Simple 1-Step Bias Checker</span>
              </div>
              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white leading-tight">
                Upload your dataset. <br />
                <span className="text-[#facc15]">See if anyone is treated unfairly.</span>
              </h1>
              <p className="text-zinc-400 text-sm md:text-base max-w-xl mx-auto leading-relaxed">
                You don't need to be a data scientist. Just drop your CSV file here. FairScan automatically finds who is in the dataset, checks if everyone gets a fair shot, and tells you the result in simple English.
              </p>

              {/* API Key Quick Trigger Banner */}
              <div className="pt-1 flex items-center justify-center">
                <button
                  type="button"
                  onClick={() => setShowKeyModal(true)}
                  className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#18181d] hover:bg-[#202026] border border-[#272730] text-xs text-zinc-300 transition hover:border-[#facc15]/50 group"
                >
                  <Key className="w-3.5 h-3.5 text-[#facc15] group-hover:rotate-45 transition-transform" />
                  <span>
                    {groqKey || geminiKey
                      ? 'Custom AI Keys Active (Click to edit)'
                      : 'Have your own Groq or Gemini API keys? Add them here'}
                  </span>
                  <span className="text-[10px] text-zinc-500 font-mono">
                    {groqKey || geminiKey ? 'Custom Keys' : 'Optional • Runs 100% offline too'}
                  </span>
                </button>
              </div>
            </div>

            {/* Drag & Drop File Zone */}
            <div className="bento-card p-12 md:p-16 flex flex-col items-center justify-center text-center cursor-pointer relative border-dashed hover:border-[#facc15] group">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleAutoAuditUpload(e.target.files[0])}
                disabled={loading}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full disabled:cursor-not-allowed"
              />
              <div className="w-16 h-16 rounded-2xl bg-[#facc15]/10 border border-[#facc15]/30 flex items-center justify-center text-[#facc15] mb-4 group-hover:scale-110 transition-transform">
                <Upload className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white">Click or drag your CSV file here</h3>
              <p className="text-xs text-zinc-400 mt-1.5 max-w-md">
                Works with any tabular CSV file (like spreadsheets with job applicants, customers, or loan approvals).
              </p>

              {loading ? (
                <div className="mt-6 flex flex-col items-center space-y-2">
                  <div className="w-6 h-6 border-2 border-[#facc15] border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-xs font-bold text-[#facc15] animate-pulse">{loadingStep}</p>
                </div>
              ) : (
                <div className="mt-5 px-5 py-2.5 rounded-full bg-white text-black font-bold text-xs shadow-md">
                  Upload & Check Now
                </div>
              )}
            </div>

            {/* Quick Demo Cards */}
            <div className="space-y-3 text-center">
              <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Or see how it works with sample examples:
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                <button
                  onClick={() => handleAutoAuditSample('hiring')}
                  disabled={loading}
                  className="bento-card p-5 hover:border-[#facc15] text-left transition group space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-white group-hover:text-[#facc15]">Job Hiring Example</span>
                    <ArrowRight className="w-4 h-4 text-zinc-500 group-hover:text-[#facc15] group-hover:translate-x-1 transition" />
                  </div>
                  <p className="text-xs text-zinc-400">
                    200 job applicants. Checks if male and female applicants got hired at fair rates.
                  </p>
                </button>

                <button
                  onClick={() => handleAutoAuditSample('lending')}
                  disabled={loading}
                  className="bento-card p-5 hover:border-[#facc15] text-left transition group space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-white group-hover:text-[#facc15]">Loan Approval Example</span>
                    <ArrowRight className="w-4 h-4 text-zinc-500 group-hover:text-[#facc15] group-hover:translate-x-1 transition" />
                  </div>
                  <p className="text-xs text-zinc-400">
                    400 bank customers. Checks if younger and older applicants got approved fairly.
                  </p>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* 2. RESULTS VIEW (Simple, Clear English)                                   */}
        {/* ========================================================================= */}
        {datasetMeta && auditData && (
          <div className="space-y-8">
            {/* Auto-Detection Plain-English Banner */}
            <div className="bento-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs border-[#facc15]/30 bg-[#111114]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="badge-yellow text-[11px] font-bold px-2 py-0.5 rounded">
                  WHAT WE FOUND
                </span>
                <span className="text-zinc-300">
                  Decision being measured: <strong className="text-white">{targetCol}</strong> (Positive Result = <strong className="text-[#facc15]">'{favorableOutcome}'</strong>)
                </span>
                <span className="text-zinc-600">•</span>
                <span className="text-zinc-300">
                  Groups compared: <strong className="text-white">{sensitiveCols.join(', ')}</strong>
                </span>
              </div>

              <button
                onClick={() => setShowConfigModal(true)}
                className="text-zinc-300 hover:text-white underline text-[11px] self-start md:self-auto"
              >
                Change these settings
              </button>
            </div>

            {/* TAB 1: AUDIT RESULTS */}
            {activeTab === 'audit' && (
              <div className="space-y-6">
                {/* 4 Big Simple Metric Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bento-card p-5">
                    <span className="text-xs text-zinc-400 font-medium">Total People Checked</span>
                    <div className="text-2xl font-mono font-bold text-white mt-1">
                      {datasetMeta.total_rows.toLocaleString()}
                    </div>
                    <span className="text-[11px] text-zinc-500 mt-0.5 block">{datasetMeta.total_columns} columns in file</span>
                  </div>

                  <div className="bento-card p-5">
                    <span className="text-xs text-zinc-400 font-medium">Average Success Rate</span>
                    <div className="text-2xl font-mono font-bold text-white mt-1">
                      {profileData?.target_profile.favorable_percentage}%
                    </div>
                    <span className="text-[11px] text-zinc-500 mt-0.5 block">
                      {profileData?.target_profile.favorable_count} got a positive decision
                    </span>
                  </div>

                  <div className="bento-card p-5 border-[#facc15]/30">
                    <span className="text-xs text-zinc-400 font-medium">Unfair Gaps Detected</span>
                    <div
                      className={`text-2xl font-mono font-bold mt-1 ${
                        findingsData?.adverse_impact_count > 0 ? 'text-[#facc15]' : 'text-emerald-400'
                      }`}
                    >
                      {findingsData?.adverse_impact_count}
                    </div>
                    <span className="text-[11px] text-zinc-500 mt-0.5 block">
                      {findingsData?.adverse_impact_count > 0 ? 'Groups facing disadvantage' : 'No major gaps found'}
                    </span>
                  </div>

                  <div className="bento-card p-5">
                    <span className="text-xs text-zinc-400 font-medium">Overall Verdict</span>
                    <div
                      className={`text-sm font-bold mt-2 flex items-center space-x-1.5 ${
                        findingsData?.adverse_impact_count > 0 ? 'text-[#facc15]' : 'text-emerald-400'
                      }`}
                    >
                      {findingsData?.adverse_impact_count > 0 ? (
                        <>
                          <AlertTriangle className="w-4 h-4 text-[#facc15]" />
                          <span>Action Needed</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          <span>Looks Balanced</span>
                        </>
                      )}
                    </div>
                    <span className="text-[11px] text-zinc-500 mt-0.5 block">Based on standard 80% rule</span>
                  </div>
                </div>

                {/* Plain-English Story Summary Box */}
                {explanationData && (
                  <div className="bento-card p-6 space-y-3 bg-[#111115] border-[#facc15]/40">
                    <div className="flex items-center justify-between border-b border-[#202026] pb-3 text-xs">
                      <div className="flex items-center space-x-2">
                        <Sparkles className="w-4 h-4 text-[#facc15]" />
                        <span className="font-bold text-white text-sm">Plain-English Summary (In Simple Words)</span>
                      </div>
                      <span className="text-zinc-400 font-mono text-[11px]">{explanationData.source}</span>
                    </div>
                    <div className="text-xs text-zinc-200 leading-relaxed whitespace-pre-line font-sans">
                      {explanationData.explanation_text}
                    </div>
                  </div>
                )}

                {/* Clear Breakdown By Group */}
                {Object.entries(auditData.attribute_audits).map(([attrName, audit]) => {
                  if (audit.status !== 'completed') return null;

                  const ref = audit.reference_group;
                  const groups = Object.keys(audit.group_stats);
                  const selectionRates = groups.map((g) => audit.group_stats[g].selection_rate_pct);

                  return (
                    <div key={attrName} className="bento-card p-6 space-y-6">
                      <div className="flex items-center justify-between border-b border-[#202026] pb-3 text-xs">
                        <div>
                          <h3 className="text-base font-bold text-white">Comparing: {attrName}</h3>
                          <p className="text-xs text-zinc-400 mt-0.5">
                            Comparison baseline group: <strong>{ref}</strong>
                          </p>
                        </div>
                        <span className="badge-yellow text-[11px] font-mono px-2.5 py-1 rounded font-bold">
                          Group Breakdown
                        </span>
                      </div>

                      {/* Visual Chart */}
                      <div className="p-4 rounded-xl bg-black/50 border border-[#202026]">
                        <span className="text-xs font-bold text-zinc-200 block mb-1">
                          Success Rate by Group (Higher bar means higher percentage of people got a positive result)
                        </span>
                        <Plot
                          data={[
                            {
                              x: groups,
                              y: selectionRates,
                              type: 'bar',
                              marker: { color: groups.map((g) => (g === ref ? '#facc15' : '#ffffff')) },
                              text: selectionRates.map((v) => `${v}%`),
                              textposition: 'auto',
                            },
                          ]}
                          layout={{
                            paper_bgcolor: 'transparent',
                            plot_bgcolor: 'transparent',
                            font: { color: '#a1a1aa', size: 11 },
                            margin: { t: 10, r: 10, l: 30, b: 35 },
                            yaxis: { range: [0, 100], gridcolor: '#202026', title: 'Success Rate (%)' },
                            xaxis: { gridcolor: '#202026' },
                            autosize: true,
                          }}
                          useResizeHandler={true}
                          style={{ width: '100%', height: '220px' }}
                        />
                      </div>

                      {/* Simple English Table */}
                      <div className="overflow-x-auto rounded-xl border border-[#202026]">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-[#18181d] text-zinc-400 border-b border-[#202026] text-[11px]">
                            <tr>
                              <th className="py-2.5 px-4 font-semibold">Group</th>
                              <th className="py-2.5 px-4 font-semibold">Total People</th>
                              <th className="py-2.5 px-4 font-semibold">Positive Results</th>
                              <th className="py-2.5 px-4 font-semibold">Success Rate</th>
                              <th className="py-2.5 px-4 font-semibold">Difference from Benchmark</th>
                              <th className="py-2.5 px-4 font-semibold">Ratio to Benchmark</th>
                              <th className="py-2.5 px-4 font-semibold">Verdict</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1e1e24] text-[11px]">
                            {groups.map((g) => {
                              const s = audit.group_stats[g];
                              const spd = audit.statistical_parity.comparisons[g];
                              const di = audit.disparate_impact.comparisons[g];
                              const isRef = g === ref;

                              return (
                                <tr key={g} className={isRef ? 'bg-white/5' : 'hover:bg-white/[0.02]'}>
                                  <td className="py-2.5 px-4 font-bold text-white">
                                    {g} {isRef && <span className="text-[10px] text-[#facc15] font-mono">(Benchmark)</span>}
                                  </td>
                                  <td className="py-2.5 px-4 text-zinc-300 font-mono">{s.total_count} people</td>
                                  <td className="py-2.5 px-4 text-zinc-300 font-mono">{s.favorable_count} positive</td>
                                  <td className="py-2.5 px-4 text-white font-bold font-mono">{s.selection_rate_pct}%</td>
                                  <td className="py-2.5 px-4 text-zinc-300 font-mono">
                                    {spd.difference_pct > 0 ? `+${spd.difference_pct}%` : `${spd.difference_pct}%`}
                                  </td>
                                  <td className="py-2.5 px-4 font-mono">
                                    {di.zero_denominator ? (
                                      <span className="text-zinc-500">No ratio</span>
                                    ) : (
                                      <span
                                        className={
                                          di.violates_80_rule
                                            ? 'text-[#facc15] font-bold bg-[#facc15]/10 px-2 py-0.5 rounded border border-[#facc15]/30'
                                            : 'text-zinc-300'
                                        }
                                      >
                                        {Math.round((di.ratio || 0) * 100)}% of benchmark
                                      </span>
                                    )}
                                  </td>
                                  <td className="py-2.5 px-4 text-xs">
                                    {isRef ? (
                                      <span className="text-zinc-400">Benchmark Base</span>
                                    ) : di.violates_80_rule ? (
                                      <span className="text-[#facc15] font-bold flex items-center space-x-1">
                                        <AlertTriangle className="w-3.5 h-3.5 text-[#facc15]" />
                                        <span>Unfair Gap</span>
                                      </span>
                                    ) : (
                                      <span className="text-emerald-400 font-semibold flex items-center space-x-1">
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                        <span>Fair (Passes 80%)</span>
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })}

                {/* Specific Alerts & Next Steps */}
                {findingsData && (
                  <div className="bento-card p-6 space-y-4">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      Specific Observations & Next Steps ({findingsData.findings.length})
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {findingsData.findings.map((f, idx) => (
                        <div
                          key={idx}
                          className={`p-4 rounded-xl border text-xs space-y-1.5 ${
                            f.type === 'critical'
                              ? 'bg-[#facc15]/5 border-[#facc15]/40 text-white'
                              : 'bg-black/40 border-[#202026] text-zinc-300'
                          }`}
                        >
                          <div className="font-bold text-white flex justify-between">
                            <span>{f.title}</span>
                            <span className="text-[10px] font-mono text-[#facc15]">[{f.attribute}]</span>
                          </div>
                          <p className="text-[11px] text-zinc-300 leading-relaxed">{f.summary}</p>
                          <p className="text-[10px] text-zinc-400 italic pt-1 border-t border-[#202026]">{f.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: FIX BIAS (MITIGATION) */}
            {activeTab === 'mitigation' && mitigationResult && (
              <div className="space-y-6">
                <div className="border-b border-[#1f1f24] pb-4 flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-white">Fix Bias: Automatic Data Balancing</h2>
                    <p className="text-xs text-zinc-400 mt-1">
                      This calculates fair mathematical weights for each row so that all demographic groups are treated with equal opportunity before you train a model.
                    </p>
                  </div>

                  <a
                    href={`${API_BASE}/download-reweighted?sensitive_col=${mitigationCol}&reference_group=${mitigationRef}&target_col=${targetCol}&favorable_outcome=${favorableOutcome}`}
                    download
                    className="px-4 py-2 rounded-xl bg-[#facc15] hover:bg-[#eab308] text-black font-bold text-xs flex items-center space-x-1.5 transition"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Balanced CSV</span>
                  </a>
                </div>

                {/* Before vs After */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="bento-card p-6 space-y-3">
                    <span className="text-xs text-zinc-400 uppercase tracking-wider block font-bold">
                      Original Data (Before)
                    </span>
                    <div className="space-y-2">
                      {Object.entries(mitigationResult.before_metrics.group_stats).map(([g, s]) => (
                        <div key={g} className="flex justify-between text-xs text-white font-mono p-2 rounded bg-black/40">
                          <span>{g}</span>
                          <span className="text-zinc-400 font-bold">{s.selection_rate_pct}% success</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-[11px] text-zinc-400 pt-2 border-t border-[#202026]">
                      Notice the unfair difference in success rates between groups in the raw data.
                    </p>
                  </div>

                  <div className="bento-card p-6 space-y-3 border-[#facc15]/40 bg-[#111115]">
                    <span className="text-xs text-[#facc15] uppercase tracking-wider block font-bold">
                      Balanced Data (After Weighting)
                    </span>
                    <div className="space-y-2">
                      {Object.entries(mitigationResult.after_metrics.group_stats).map(([g, s]) => (
                        <div key={g} className="flex justify-between text-xs text-white font-mono p-2 rounded bg-[#facc15]/10 border border-[#facc15]/20">
                          <span className="font-bold">{g}</span>
                          <span className="text-[#facc15] font-bold">{s.selection_rate_pct}% success</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-[11px] text-[#facc15] pt-2 border-t border-[#facc15]/20">
                      Success rates are now equalized across all groups without changing any person's actual record!
                    </p>
                  </div>
                </div>

                {/* Simple Multiplier Table */}
                <div className="bento-card p-6 space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    How Each Row Was Re-Weighted
                  </h4>
                  <div className="overflow-x-auto rounded-xl border border-[#202026]">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-[#18181d] text-zinc-400 border-b border-[#202026] text-[11px] font-sans">
                        <tr>
                          <th className="py-2.5 px-4">Group</th>
                          <th className="py-2.5 px-4">Decision Outcome</th>
                          <th className="py-2.5 px-4">Number of People</th>
                          <th className="py-2.5 px-4">Importance Multiplier</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1e1e24] text-[11px]">
                        {mitigationResult.weight_multipliers.map((m, idx) => (
                          <tr key={idx} className="hover:bg-white/[0.02]">
                            <td className="py-2 px-4 text-white font-bold">{m.group}</td>
                            <td className="py-2 px-4 text-zinc-300">{m.outcome}</td>
                            <td className="py-2 px-4 text-zinc-400">{m.joint_frequency} people</td>
                            <td className="py-2 px-4 text-[#facc15] font-bold">{m.sample_weight}x weight</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: DOWNLOAD REPORT */}
            {activeTab === 'report' && (
              <div className="space-y-6 max-w-2xl mx-auto py-6">
                <div className="bento-card p-10 text-center space-y-4">
                  <div className="w-16 h-16 rounded-2xl bg-[#facc15]/10 border border-[#facc15]/30 flex items-center justify-center text-[#facc15] mx-auto">
                    <FileText className="w-8 h-8" />
                  </div>

                  <div>
                    <h3 className="text-lg font-bold text-white">Download PDF Audit Report</h3>
                    <p className="text-xs text-zinc-400 mt-1.5 max-w-md mx-auto leading-relaxed">
                      Generates a formal, printable PDF document summarizing all findings, numbers, and plain-English recommendations.
                    </p>
                  </div>

                  <div className="pt-2">
                    <a
                      href={`${API_BASE}/report/pdf`}
                      download="fairscan_audit_report.pdf"
                      className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-[#facc15] hover:bg-[#eab308] text-black text-xs font-bold transition hover:scale-[1.02]"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download PDF Report</span>
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: RAW DATA INSPECTOR */}
            {activeTab === 'data' && (
              <div className="space-y-6">
                <div className="bento-card overflow-hidden">
                  <div className="px-5 py-3 border-b border-[#202026] text-xs font-bold text-white uppercase tracking-wider">
                    Uploaded File Preview ({datasetMeta.filename})
                  </div>
                  <div className="overflow-x-auto max-h-96">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-[#18181d] text-zinc-400 border-b border-[#202026] font-sans text-[11px]">
                        <tr>
                          {datasetMeta.columns.map((c) => (
                            <th key={c.name} className="py-2.5 px-4">{c.name}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1e1e24] text-[11px]">
                        {datasetMeta.preview_rows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-white/[0.02]">
                            {datasetMeta.columns.map((c) => (
                              <td key={c.name} className="py-2 px-4 text-zinc-300 truncate max-w-xs">
                                {row[c.name] === null ? <span className="text-zinc-600">null</span> : String(row[c.name])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Tweak Parameters Modal */}
      {showConfigModal && datasetMeta && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111114] border border-[#272730] rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202026] pb-3">
              <h3 className="text-sm font-bold text-white">Adjust Measured Columns</h3>
              <button onClick={() => setShowConfigModal(false)} className="text-zinc-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-zinc-300 font-semibold block mb-1">Target Decision Column</label>
                <select
                  value={targetCol}
                  onChange={(e) => {
                    setTargetCol(e.target.value);
                    const colObj = datasetMeta.columns.find((c) => c.name === e.target.value);
                    if (colObj && colObj.sample_values.length > 0) {
                      setFavorableOutcome(String(colObj.sample_values[0]));
                    }
                  }}
                  className="w-full bg-[#18181d] border border-[#272730] rounded-lg p-2 text-white"
                >
                  {datasetMeta.columns.map((c) => (
                    <option key={c.name} value={c.name}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-zinc-300 font-semibold block mb-1">What value is considered a positive decision?</label>
                <select
                  value={favorableOutcome}
                  onChange={(e) => setFavorableOutcome(e.target.value)}
                  className="w-full bg-[#18181d] border border-[#272730] rounded-lg p-2 text-white"
                >
                  {datasetMeta.columns
                    .find((c) => c.name === targetCol)
                    ?.sample_values.map((v) => (
                      <option key={String(v)} value={String(v)}>{String(v)}</option>
                    ))}
                </select>
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  onClick={() => setShowConfigModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-zinc-700 text-xs text-zinc-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCustomAuditReRun}
                  className="px-4 py-1.5 rounded-lg bg-[#facc15] hover:bg-[#eab308] text-black font-bold text-xs"
                >
                  Re-Check With New Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Provider & API Keys Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111114] border border-[#272730] rounded-2xl p-6 max-w-lg w-full space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202026] pb-3">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-[#facc15]/10 border border-[#facc15]/30 flex items-center justify-center text-[#facc15]">
                  <Key className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">AI Provider & API Keys</h3>
                  <p className="text-[11px] text-zinc-400">Add your keys to generate plain-English explanations</p>
                </div>
              </div>
              <button
                onClick={() => setShowKeyModal(false)}
                className="text-zinc-400 hover:text-white text-sm p-1 rounded-lg hover:bg-zinc-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Groq API Key */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-zinc-200 font-semibold flex items-center space-x-2">
                    <span>Groq API Key</span>
                    <span className="text-[10px] text-[#facc15] font-mono font-bold bg-[#facc15]/10 px-1.5 py-0.5 rounded border border-[#facc15]/20">
                      Ultra-Fast (Recommended)
                    </span>
                  </label>
                  <a
                    href="https://console.groq.com/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-[#facc15] hover:underline flex items-center space-x-1"
                  >
                    <span>Get Free Key</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                </div>
                <div className="relative">
                  <input
                    type={showGroqKey ? 'text' : 'password'}
                    placeholder="gsk_..."
                    value={groqKey}
                    onChange={(e) => setGroqKey(e.target.value)}
                    className="w-full bg-[#18181d] border border-[#272730] rounded-lg p-2.5 pr-9 text-white font-mono text-xs focus:border-[#facc15] focus:outline-none transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGroqKey(!showGroqKey)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white"
                  >
                    {showGroqKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[10px] text-zinc-500">
                  Powers instant plain-English summaries using models like Qwen 27B and Llama 3.3.
                </p>
              </div>

              {/* Gemini API Key */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-zinc-200 font-semibold flex items-center space-x-2">
                    <span>Google Gemini API Key</span>
                    <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-1.5 py-0.5 rounded">
                      Gemini 2.5 Flash
                    </span>
                  </label>
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-[#facc15] hover:underline flex items-center space-x-1"
                  >
                    <span>Get Free Key</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                </div>
                <div className="relative">
                  <input
                    type={showGeminiKey ? 'text' : 'password'}
                    placeholder="AIzaSy..."
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    className="w-full bg-[#18181d] border border-[#272730] rounded-lg p-2.5 pr-9 text-white font-mono text-xs focus:border-[#facc15] focus:outline-none transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGeminiKey(!showGeminiKey)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white"
                  >
                    {showGeminiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Provider Selection */}
              <div className="space-y-1.5">
                <label className="text-zinc-200 font-semibold block">Preferred AI Provider</label>
                <select
                  value={llmProvider}
                  onChange={(e) => setLlmProvider(e.target.value)}
                  className="w-full bg-[#18181d] border border-[#272730] rounded-lg p-2.5 text-white text-xs focus:border-[#facc15] focus:outline-none"
                >
                  <option value="auto">Auto (Best Available: Groq → Gemini → Offline)</option>
                  <option value="groq">Groq AI (Ultra Fast)</option>
                  <option value="gemini">Google Gemini (Gemini 2.5 Flash)</option>
                  <option value="deterministic">Offline Mode (No API Keys Needed)</option>
                </select>
              </div>

              {/* Privacy Notice */}
              <div className="p-3 rounded-xl bg-black/40 border border-[#202026] text-[11px] text-zinc-400 flex items-start space-x-2.5">
                <Shield className="w-4 h-4 text-[#facc15] shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="text-zinc-200 block">100% Client-Side Privacy:</strong>
                  Your API keys are stored only in your local browser and sent directly to compute aggregated group summaries. We never log or store raw datasets or your API keys.
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-between border-t border-[#202026]">
                <button
                  type="button"
                  onClick={() => {
                    clearApiKeys();
                    setSavedKeyFeedback(true);
                    setTimeout(() => setSavedKeyFeedback(false), 2000);
                  }}
                  className="text-zinc-500 hover:text-red-400 text-xs transition"
                >
                  Clear Keys
                </button>
                <div className="flex items-center space-x-2">
                  {savedKeyFeedback && (
                    <span className="text-xs text-emerald-400 font-medium flex items-center space-x-1 animate-fadeIn">
                      <Check className="w-3.5 h-3.5" />
                      <span>Saved!</span>
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      saveApiKeys(groqKey, geminiKey, llmProvider);
                      setShowKeyModal(false);
                    }}
                    className="px-4 py-2 rounded-xl bg-[#facc15] hover:bg-[#eab308] text-black font-bold text-xs shadow-md transition"
                  >
                    Save & Apply
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-[#1f1f24] bg-[#0c0c0f] px-6 py-4 text-xs text-zinc-500 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FairScanLogo className="w-4 h-4" />
          <span className="text-white font-medium">FairScan</span>
          <span>• Plain-English Dataset Fairness Platform</span>
        </div>
        <div>
          Based on the standard 80% fairness rule & EU AI Act guidance
        </div>
      </footer>
    </div>
  );
}
