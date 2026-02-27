import React, { useState } from 'react';
import { 
  Play, Pause, SkipForward, SkipBack, Search, 
  Settings, Zap, CheckCircle2, MessageSquare, 
  ChevronRight, Download, Video, Info, 
  ChevronDown, Plus, Monitor, Terminal, FileCode2,
  Folder, FileJson, FileText, ChevronRight as ChevronRightIcon,
  Circle, MoreHorizontal, Maximize2, X, Minus, FolderOpen,
  Volume2, Film
} from 'lucide-react';

/**
 * TISS Sports Agentic System - IDE Layout
 * Exact match of the provided reference image
 */

const INITIAL_MESSAGES = [
  { 
    role: 'user', 
    title: 'Hardware board connection check',
    content: 'check which hardware board is connected' 
  },
  { 
    role: 'agent', 
    content: `**Two COM ports detected:**\n\n• **COM1:** Communications Port (standard PC port)\n• **COM4:** USB Serial Device (likely your hardware board)\n\nThe COM4 port (USB VID:PID=0483:374B) is typical for **STMicroelectronics devices** (likely an STM32 board).\n\nWould you like me to get more details about the board? I can try to identify it by checking if it's a known STM32 configuration or query PlatformIO for board information.`
  },
  {
    role: 'user',
    content: 'how do you know its a stm32 board'
  },
  {
    role: 'agent',
    content: `I made an educated guess based on the USB identifier:\n\n• **VID:PID = 0483:374B** — This is the USB Vendor ID for **STMicroelectronics**\n\nThe \`0483\` is ST's vendor ID, and \`374B\` is commonly used for STM32 DFU (Device Firmware Upgrade) or ST-LINK programmers.\n\nHowever, this doesn't definitively prove it's an STM32 — it could also be:\n\n• An ST-LINK debug probe\n• Another ST-based device\n\n**To confirm, you could:**\n\n1. Connect to the device and check the firmware/bootloader messages\n2. Check PlatformIO board definitions`
  }
];

const FILE_TREE = [
  { name: '.expo', type: 'folder' },
  { name: 'app', type: 'folder' },
  { name: 'assets', type: 'folder' },
  { name: 'node_modules', type: 'folder' },
  { name: '.env.example', type: 'file', icon: FileText, color: 'text-slate-400' },
  { name: '.gitignore', type: 'file', icon: FileCode2, color: 'text-orange-500' },
  { name: 'app.d.ts', type: 'file', icon: FileCode2, color: 'text-blue-400' },
  { name: 'app.json', type: 'file', icon: FileJson, color: 'text-yellow-400' },
  { name: 'babel.config.js', type: 'file', icon: FileCode2, color: 'text-yellow-400' },
  { name: 'BUILD_SUMMARY.md', type: 'file', icon: Info, color: 'text-blue-400' },
  { name: 'bun.lock', type: 'file', icon: FileText, color: 'text-slate-200' },
  { name: 'DEPLOYMENT.md', type: 'file', icon: Info, color: 'text-blue-400' },
  { name: 'expo_debug.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'expo_output.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'expo_web_2.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'expo_web_3.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'expo_web_4.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'expo_web_5.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'expo_web_6.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'expo_web.log', type: 'file', icon: FileText, color: 'text-lime-500' },
  { name: 'package-lock.json', type: 'file', icon: FileJson, color: 'text-yellow-400' },
  { name: 'package.json', type: 'file', icon: FileJson, color: 'text-yellow-400' },
  { name: 'postcss.config.js', type: 'file', icon: FileCode2, color: 'text-yellow-400' },
  { name: 'README.md', type: 'file', icon: Info, color: 'text-blue-400' },
  { name: 'tailwind.config.js', type: 'file', icon: FileCode2, color: 'text-blue-400' },
  { name: 'tsconfig.json', type: 'file', icon: FileJson, color: 'text-blue-400' },
];

export default function App() {
  const [inputValue, setInputValue] = useState('');

  // Renders the rich text for the agent messages
  const renderMessageContent = (content) => {
    return content.split('\n').map((line, i) => {
      if (line.startsWith('•')) {
        return <div key={i} className="pl-4 my-1">{line}</div>;
      }
      if (line.match(/^\d\./)) {
        return <div key={i} className="pl-4 my-1 text-slate-300">{line}</div>;
      }
      if (line === '') {
        return <br key={i} />;
      }
      // Simple bold parsing
      const parts = line.split(/(\*\*.*?\*\*)/g);
      return (
        <div key={i} className="my-1 text-slate-300 leading-relaxed">
          {parts.map((part, j) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={j} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
            }
            // Code parsing
            const codeParts = part.split(/(\`.*?\`)/g);
            return codeParts.map((cp, k) => {
              if (cp.startsWith('`') && cp.endsWith('`')) {
                 return <span key={k} className="bg-slate-800 text-orange-300 px-1 rounded font-mono text-[13px]">{cp.slice(1, -1)}</span>;
              }
              return <span key={k}>{cp}</span>;
            });
          })}
        </div>
      );
    });
  };

  return (
    <div className="h-screen w-full flex flex-col bg-[#09090B] text-slate-300 font-sans overflow-hidden selection:bg-lime-500/30">
      {/* 1. TOP TITLE BAR */}
      <header className="h-10 shrink-0 flex items-center justify-between px-3 border-b border-white/5 bg-[#09090B] select-none">
        {/* Left: Sidebar toggle + Search */}
        <div className="flex items-center gap-4 w-1/3">
          <div className="flex items-center gap-2">
            <LayoutGrid size={16} className="text-slate-400 cursor-pointer hover:text-white" />
          </div>
          <div className="flex-1 max-w-sm flex items-center bg-[#18181B] border border-white/5 rounded-md px-3 py-1.5 cursor-text group hover:border-white/10 transition-colors">
            <Search size={14} className="text-slate-500 mr-2" />
            <span className="text-xs text-slate-400 flex-1">Search conow-energy</span>
            <span className="text-[10px] text-slate-500 font-mono">Ctrl+P</span>
          </div>
        </div>

        {/* Center: Logo */}
        <div className="flex items-center justify-center gap-2 w-1/3">
          <div className="w-5 h-5 rounded bg-lime-400 flex items-center justify-center shadow-[0_0_10px_rgba(173,255,0,0.2)]">
            <Zap className="text-black w-3.5 h-3.5" fill="black" />
          </div>
          <span className="font-bold text-sm tracking-tight text-white">TISS <span className="text-lime-400">ARENA</span></span>
        </div>

        {/* Right: Actions & Window Controls */}
        <div className="flex items-center justify-end gap-3 w-1/3">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#18181B] border border-white/5 cursor-pointer hover:bg-white/5">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs font-medium text-slate-300">Status</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#18181B] border border-white/5 cursor-pointer hover:bg-white/5">
            <FolderOpen size={14} className="text-yellow-400" />
            <span className="text-xs font-medium text-slate-300">Open</span>
          </div>
          <button className="px-3 py-1 text-xs font-medium bg-[#18181B] border border-white/5 rounded text-slate-300 hover:text-white hover:bg-white/5">
            Share
          </button>
          
          {/* OS Window Controls */}
          <div className="flex items-center gap-3 ml-2 text-slate-500">
            <Minus size={14} className="hover:text-white cursor-pointer" />
            <Maximize2 size={12} className="hover:text-white cursor-pointer" />
            <X size={16} className="hover:text-white cursor-pointer" />
          </div>
        </div>
      </header>

      {/* MAIN WORKSPACE */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        
        {/* 2. FAR LEFT ACTIVITY BAR */}
        <nav className="w-12 shrink-0 flex flex-col items-center py-3 border-r border-white/5 bg-[#09090B] gap-4">
          <div className="w-8 h-8 rounded bg-teal-900/50 border border-teal-500/30 flex items-center justify-center text-teal-400 font-bold text-sm cursor-pointer">
            C
          </div>
          <div className="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-white cursor-pointer">
            <Plus size={20} />
          </div>
          <div className="mt-auto mb-2 w-8 h-8 flex items-center justify-center text-slate-500 hover:text-white cursor-pointer">
            <Settings size={20} />
          </div>
        </nav>

        {/* 3. LEFT PANEL: CHAT INTERFACE */}
        <aside className="w-[450px] shrink-0 flex flex-col border-r border-white/5 bg-[#09090B] relative">
          {/* Chat Header inside message area */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-6">
            {INITIAL_MESSAGES.map((msg, idx) => (
              <div key={idx} className="flex flex-col gap-2">
                {msg.role === 'user' ? (
                  <div className="bg-[#18181B] border border-white/5 rounded-lg p-3 w-full">
                    {msg.title && <h3 className="text-sm font-semibold text-white mb-2">{msg.title}</h3>}
                    <div className="text-sm text-slate-300 bg-[#09090B]/50 p-2 rounded border border-white/5 font-mono">
                      {msg.content}
                    </div>
                    {msg.title && <div className="mt-2 text-[10px] text-slate-500 flex items-center gap-1">
                      <ChevronDown size={10}/> Show steps · 48s
                    </div>}
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Response</div>
                    <div className="text-sm">
                      {renderMessageContent(msg.content)}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {/* Down Arrow Indicator */}
            <div className="flex justify-center mt-2">
               <div className="w-6 h-6 rounded-full border border-white/10 flex items-center justify-center text-slate-500 bg-[#18181B] cursor-pointer hover:text-white hover:border-white/30">
                 <ChevronDown size={14} />
               </div>
            </div>
          </div>

          {/* Chat Input Area */}
          <div className="p-4 bg-[#09090B]">
            <div className="bg-[#18181B] border border-white/10 rounded-xl overflow-hidden shadow-lg shadow-black/50 focus-within:border-lime-500/50 transition-colors">
              <textarea 
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder='Ask anything... "Generate API documentation"'
                className="w-full bg-transparent text-sm p-3 min-h-[60px] resize-none focus:outline-none placeholder:text-slate-600 custom-scrollbar"
              />
              <div className="flex items-center justify-between px-3 py-2 bg-[#18181B] border-t border-white/5">
                <div className="flex items-center gap-3">
                   <button className="text-xs font-medium text-slate-400 hover:text-white flex items-center gap-1">
                     Build <ChevronDown size={12} />
                   </button>
                   <button className="text-xs font-medium text-slate-300 flex items-center gap-1.5 bg-[#27272A] px-2 py-1 rounded">
                     <span className="w-3 h-3 bg-white text-black text-[8px] font-bold flex items-center justify-center rounded-sm">Σ</span>
                     MiniMax M2.5 Free
                   </button>
                </div>
                <div className="flex items-center gap-2">
                   <button className="p-1.5 text-slate-500 hover:text-white rounded-md"><Target size={14}/></button>
                   <button className="p-1.5 text-slate-500 hover:text-white rounded-md"><Upload size={14}/></button>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* 4. CENTER PANEL: VIDEO & TIMELINE (The Focus Area) */}
        <section className="flex-1 flex flex-col p-4 bg-[#09090B] min-w-0">
          <div className="flex-1 border border-[#8B5CF6] rounded-xl overflow-hidden flex flex-col shadow-[0_0_20px_rgba(139,92,246,0.15)] relative">
            
            {/* Top Half: Video Player Area */}
            <div className="flex-1 bg-[#0B1120] relative flex items-center justify-center overflow-hidden">
               {/* "Live Analytics Feed" badge */}
               <div className="absolute top-4 left-4 z-10">
                 <div className="bg-[#0B1120]/80 border border-lime-400/30 rounded px-2 py-1 flex items-center gap-2">
                   <div className="w-1.5 h-1.5 rounded-full bg-lime-400 animate-pulse shadow-[0_0_5px_#ADFF00]" />
                   <span className="text-[10px] font-mono text-lime-400 font-bold tracking-widest">LIVE ANALYTICS FEED</span>
                 </div>
               </div>

               {/* Video Center Placeholder */}
               <div className="flex flex-col items-center text-[#1E293B]">
                  <Video size={80} strokeWidth={1} />
                  <div className="mt-6 text-sm font-mono tracking-widest opacity-80 uppercase">
                    Previewing: Left-foot strike from outside the box
                  </div>
               </div>
            </div>

            {/* Bottom Half: Media Tracks Timeline */}
            <div className="h-44 bg-[#0B0D0F] border-t border-[#8B5CF6]/30 flex flex-col shrink-0">
              {/* Timeline Header */}
              <div className="h-10 px-4 flex items-center justify-between border-b border-white/5">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 bg-[#18181B] px-2 py-1 rounded border border-white/5">
                    <Activity size={12} className="text-lime-400" />
                    <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Media Tracks</span>
                  </div>
                  <div className="h-3 w-px bg-slate-700" />
                  <span className="font-mono text-[11px] text-lime-400">00:12:34:08</span>
                </div>
                <Settings size={14} className="text-slate-500 cursor-pointer hover:text-white" />
              </div>

              {/* Tracks Area */}
              <div className="flex-1 flex relative overflow-hidden">
                {/* Playhead */}
                <div className="absolute inset-y-0 left-1/3 w-px bg-white z-20 shadow-[0_0_8px_rgba(255,255,255,0.8)]">
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-white rounded-full shadow-[0_0_5px_white]" />
                </div>

                {/* Track Headers (Left Column) */}
                <div className="w-14 flex flex-col border-r border-white/5 bg-[#09090B] shrink-0 z-10">
                  <div className="flex-1 flex flex-col items-center justify-center border-b border-white/5 gap-1">
                     <Film size={14} className="text-slate-500" />
                     <span className="text-[9px] font-bold text-slate-600">V1</span>
                  </div>
                  <div className="flex-1 flex flex-col items-center justify-center gap-1">
                     <Volume2 size={14} className="text-slate-500" />
                     <span className="text-[9px] font-bold text-slate-600">A1</span>
                  </div>
                </div>

                {/* Tracks Content */}
                <div className="flex-1 flex flex-col relative overflow-hidden">
                  {/* Grid Lines Overlay */}
                  <div className="absolute inset-0 flex">
                     {[...Array(10)].map((_, i) => (
                       <div key={i} className="flex-1 border-r border-white/5 h-full pointer-events-none" />
                     ))}
                  </div>

                  {/* V1 Track */}
                  <div className="flex-1 border-b border-white/5 flex items-center relative py-2">
                     <div className="absolute left-[10%] w-[12%] h-full rounded bg-[#1E1B4B]/80 border border-indigo-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.15)]">
                       <span className="text-xl">⚽</span>
                     </div>
                     <div className="absolute left-[25%] w-[8%] h-full rounded bg-[#1E1B4B]/80 border border-indigo-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.15)]">
                       <span className="text-xl">🧤</span>
                     </div>
                     {/* Playhead intersecting clip */}
                     <div className="absolute left-[33%] w-[15%] h-full rounded bg-amber-900/30 border border-amber-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(245,158,11,0.15)]">
                       <span className="text-xl">⚠️</span>
                     </div>
                     <div className="absolute left-[65%] w-[10%] h-full rounded bg-[#1E1B4B]/80 border border-indigo-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.15)]">
                       <span className="text-xl">⚽</span>
                     </div>
                  </div>

                  {/* A1 Track */}
                  <div className="flex-1 flex items-center relative px-1">
                    <div className="w-full h-full flex items-center gap-[1px]">
                      {[...Array(150)].map((_, i) => {
                         // Create a pseudo-realistic audio wave pattern
                         let h = 20 + Math.random() * 30;
                         if (i > 45 && i < 55) h = 70 + Math.random() * 30; // Peak 1
                         if (i > 95 && i < 110) h = 80 + Math.random() * 20; // Peak 2
                         return (
                           <div key={i} className="flex-1 bg-[#0D9488]/60" style={{ height: `${h}%` }} />
                         );
                      })}
                    </div>
                    {/* Centered waveform line */}
                    <div className="absolute inset-x-0 top-1/2 h-px bg-[#0D9488]/80 pointer-events-none" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 5. RIGHT PANEL: FILE EXPLORER */}
        <aside className="w-64 shrink-0 border-l border-white/5 bg-[#09090B] flex flex-col">
          {/* Tabs */}
          <div className="flex h-10 border-b border-white/5">
             <button className="flex-1 text-[11px] font-medium text-slate-500 hover:text-slate-300">0 Changes</button>
             <button className="flex-1 text-[11px] font-medium text-white bg-[#18181B] border-t-2 border-t-lime-500">All files</button>
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar py-2">
            {FILE_TREE.map((item, idx) => (
              <div key={idx} className="flex items-center gap-1.5 px-4 py-1 hover:bg-[#18181B] cursor-pointer group">
                {item.type === 'folder' ? (
                  <>
                    <ChevronRightIcon size={12} className="text-slate-500 group-hover:text-slate-300 transition-colors" />
                    <span className="text-xs text-slate-300">{item.name}</span>
                  </>
                ) : (
                  <>
                    <div className="w-3" /> {/* Spacer for file alignment */}
                    <item.icon size={12} className={item.color} />
                    <span className="text-xs text-slate-400 group-hover:text-slate-200 transition-colors">{item.name}</span>
                  </>
                )}
              </div>
            ))}
          </div>

          <div className="p-4 border-t border-white/5 bg-[#09090B]">
             <div className="text-xs font-semibold text-slate-300">Activate Windows</div>
             <div className="text-[10px] text-slate-500 mt-1">Go to Settings to activate Windows.</div>
          </div>
        </aside>

      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #27272A; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #3F3F46; }
      `}} />
    </div>
  );
}