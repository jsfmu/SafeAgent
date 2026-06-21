import { Briefcase, HeadphonesIcon, Search, Mail, Code2, BarChart2, Shield, FileText } from "lucide-react";

interface Template {
  id: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  prompt: string;
  risk: "low" | "medium" | "high";
  domain: string;
}

const TEMPLATES: Template[] = [
  {
    id: "hiring",
    icon: <Briefcase size={20} />,
    title: "Hiring Agent",
    description: "Screen resumes, score candidates on merit, email shortlist",
    prompt: "Hiring agent — screen resumes, score candidates on skills and experience only, email top 5 to hiring manager. Merit-based, no demographic bias.",
    risk: "high",
    domain: "HR",
  },
  {
    id: "support",
    icon: <HeadphonesIcon size={20} />,
    title: "Customer Support",
    description: "Classify tickets, draft replies, escalate critical issues",
    prompt: "Customer support agent — classify incoming tickets by urgency, draft polite replies, automatically escalate billing and legal issues to human agents.",
    risk: "medium",
    domain: "Support",
  },
  {
    id: "research",
    icon: <Search size={20} />,
    title: "Research Agent",
    description: "Search web, summarize sources, write cited report",
    prompt: "Research agent — search the web for information, summarize multiple sources, cite evidence, and write a structured report. Flag any conflicting information.",
    risk: "low",
    domain: "Research",
  },
  {
    id: "email",
    icon: <Mail size={20} />,
    title: "Email Triage",
    description: "Prioritize inbox, draft responses, flag urgent items",
    prompt: "Email triage agent — read incoming emails, prioritize by urgency, draft response templates, and flag emails requiring immediate human attention.",
    risk: "medium",
    domain: "Productivity",
  },
  {
    id: "code",
    icon: <Code2 size={20} />,
    title: "Code Review",
    description: "Analyse PRs, flag issues, suggest improvements",
    prompt: "Code review agent — analyse pull requests for bugs, security vulnerabilities, and code quality issues. Suggest improvements and flag critical security issues for human review.",
    risk: "low",
    domain: "Engineering",
  },
  {
    id: "data",
    icon: <BarChart2 size={20} />,
    title: "Data Pipeline",
    description: "Fetch data, clean it, generate insights report",
    prompt: "Data pipeline agent — fetch data from APIs, clean and normalise it, run basic analysis, and generate an insights report. Never delete source data.",
    risk: "medium",
    domain: "Analytics",
  },
  {
    id: "compliance",
    icon: <Shield size={20} />,
    title: "Compliance Monitor",
    description: "Scan documents, flag policy violations, log findings",
    prompt: "Compliance monitoring agent — scan documents and communications for policy violations, flag issues for human review, and log all findings to the audit trail.",
    risk: "high",
    domain: "Legal",
  },
  {
    id: "content",
    icon: <FileText size={20} />,
    title: "Content Moderator",
    description: "Review content, flag violations, escalate edge cases",
    prompt: "Content moderation agent — review user-generated content, automatically remove clear violations, flag edge cases for human review, never make final decisions on borderline content without human approval.",
    risk: "high",
    domain: "Trust & Safety",
  },
];

const RISK_STYLES = {
  low:    { badge: "bg-emerald-100 text-emerald-700 border-emerald-200", dot: "bg-emerald-500", label: "Low risk" },
  medium: { badge: "bg-amber-100 text-amber-700 border-amber-200",       dot: "bg-amber-500",   label: "Med risk" },
  high:   { badge: "bg-red-100 text-red-700 border-red-200",             dot: "bg-red-500",     label: "High risk" },
};

interface Props {
  onSelect: (prompt: string) => void;
}

export function UseCaseGallery({ onSelect }: Props) {
  return (
    <div className="mb-6">
      <p className="text-xs text-emerald-600 font-semibold uppercase tracking-wide mb-3">
        Start from a template
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {TEMPLATES.map((t) => {
          const rs = RISK_STYLES[t.risk];
          return (
            <button
              key={t.id}
              onClick={() => onSelect(t.prompt)}
              className="text-left bg-white border-2 border-emerald-100 hover:border-emerald-400 rounded-xl p-3 transition-all hover:shadow-md group"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="text-emerald-600 group-hover:text-emerald-500">{t.icon}</div>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${rs.badge}`}>
                  {rs.label}
                </span>
              </div>
              <div className="font-bold text-emerald-900 text-sm">{t.title}</div>
              <div className="text-xs text-emerald-500 mt-0.5 leading-snug">{t.description}</div>
              <div className="text-[10px] text-emerald-400 mt-1.5 font-medium">{t.domain}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
