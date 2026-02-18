"use client";

import { ReactNode, useState } from "react";

type Tab = {
  id: string;
  label: string;
  icon?: ReactNode;
};

type TabsProps = {
  tabs: Tab[];
  defaultTab?: string;
  children: (activeTab: string) => ReactNode;
  onChange?: (tabId: string) => void;
};

export default function Tabs({ tabs, defaultTab, children, onChange }: TabsProps) {
  const [localTab, setLocalTab] = useState(defaultTab || tabs[0]?.id);
  const isControlled = defaultTab !== undefined && !!onChange;
  const activeTab = isControlled ? defaultTab : localTab;

  const handleTabChange = (tabId: string) => {
    if (!isControlled) {
      setLocalTab(tabId);
    }
    onChange?.(tabId);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-1 p-1 rounded-xl bg-slate-900/50 border border-[var(--line)] overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-400/30"
                : "text-[var(--text-secondary)] hover:text-slate-100 hover:bg-slate-800/50"
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>
      <div className="min-h-0">{children(activeTab)}</div>
    </div>
  );
}

type TabPanelProps = {
  children: ReactNode;
  isActive: boolean;
};

export function TabPanel({ children, isActive }: TabPanelProps) {
  if (!isActive) return null;
  return <div>{children}</div>;
}
