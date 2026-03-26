/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { ChevronLeft, Plus, X, Search, Trash2, Edit2, Check, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  defaultDropAnimationSideEffects,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { restrictToWindowEdges } from '@dnd-kit/modifiers';

// --- Types ---

type View = 'home' | 'detail' | 'trash';

interface Page {
  id: string;
  title: string;
  content: string;
  isDeleted: boolean;
  folderId: string | null;
}

interface Folder {
  id: string;
  color: string;
  title: string;
}

// --- Constants ---

const FOLDER_COLORS = [
  '#C9F0FD', // Blue
  '#D9F0D9', // Green
  '#FDC9C9', // Red
  '#FDC9FD', // Purple
  '#FDE4C9', // Orange
  '#FDC9E4', // Pink
  '#C9FDE4', // Teal
  '#E4C9FD', // Lavender
];

// --- Components ---

function Logo({ onClick, className = "absolute top-1 left-8", size = "60" }: { onClick: () => void, className?: string, size?: string }) {
  return (
    <button 
      onClick={onClick}
      className={`${className} flex items-center gap-2 hover:scale-110 transition-transform active:scale-95`}
    >
      <svg width={size} height={size} viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M198.364 207.795C202.862 215.452 212.607 218.63 220.776 215.148C244.751 204.929 292.992 187.88 325.167 199.873C345.857 207.585 368.674 230.573 378.154 240.832C380.811 243.708 380.814 248.04 378.16 250.919C368.688 261.192 345.879 284.213 325.167 291.873C293.485 303.59 246.416 286.869 222.058 276.332C213.404 272.589 202.99 276.371 198.825 284.829C185.062 312.781 154.32 365.991 127.167 347.873C90.6714 323.52 175.054 289.207 173.167 245.373C171.444 205.338 96.6353 179.604 127.167 153.65C150.552 133.773 183.507 182.501 198.364 207.795Z" fill="#131518"/>
</svg>
    </button>
  );
}

interface PillItemProps {
  label: string;
  variant?: 'default' | 'red';
  onClick?: () => void;
  onDelete?: () => void;
  onRestore?: () => void;
  selected?: boolean;
  onToggleSelection?: () => void;
}

function PillItem({ 
  label, 
  variant = 'default', 
  onClick,
  onDelete,
  onRestore,
  selected,
  onToggleSelection,
}: PillItemProps) {
  return (
    <div className="relative group w-full flex items-center gap-3">
      {onToggleSelection && (
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onToggleSelection();
          }}
          className={`
            w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all
            ${selected ? 'bg-black border-black text-white' : 'border-black/10 hover:border-black/30 bg-white'}
          `}
        >
          {selected && <Check className="w-3 h-3" strokeWidth={3} />}
        </button>
      )}
      <div className="relative flex-1">
        <button 
          onClick={onClick}
          className={`
            w-full py-4 px-6 rounded-full text-sm font-medium transition-all active:scale-95
            ${variant === 'red' ? 'text-[#FF5A5A]' : 'text-black'}
            bg-black/5 hover:bg-black/10 text-left truncate
          `}
        >
          {label}
        </button>
        
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onRestore && (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                onRestore();
              }}
              className="p-2 hover:text-green-500 transition-colors"
              title="Restaurer"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
          {onDelete && (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-2 hover:text-red-500 transition-colors"
              title="Supprimer"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function SortablePageItem({ page, onDelete, onRestore, onClick, selected, onToggleSelection }: { 
  page: Page; 
  onDelete: (id: string) => void;
  onRestore?: (id: string) => void;
  onClick: (page: Page) => void;
  selected?: boolean;
  onToggleSelection?: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: page.id });

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <PillItem 
        label={page.title}
        variant={page.title === 'Idées vidéos' ? 'red' : 'default'}
        onClick={() => onClick(page)}
        onDelete={() => onDelete(page.id)}
        onRestore={onRestore ? () => onRestore(page.id) : undefined}
        selected={selected}
        onToggleSelection={onToggleSelection}
      />
    </div>
  );
}

function SortableFolder({ 
  folder, 
  pages, 
  onPageDelete, 
  onPageClick,
  onFolderDelete,
  onFolderRename,
  onColorChange 
}: { 
  folder: Folder; 
  pages: Page[];
  onPageDelete: (id: string) => void;
  onPageClick: (page: Page) => void;
  onFolderDelete: (id: string) => void;
  onFolderRename: (id: string, title: string) => void;
  onColorChange: (id: string, color: string) => void;
}) {
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [isEditing, setEditing] = useState(false);
  const [tempTitle, setTempTitle] = useState(folder.title);
  const pickerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: folder.id, disabled: isEditing });

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowColorPicker(false);
      }
    };
    if (showColorPicker) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showColorPicker]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleRenameSubmit = () => {
    if (tempTitle.trim()) {
      onFolderRename(folder.id, tempTitle.trim());
    } else {
      setTempTitle(folder.title);
    }
    setEditing(false);
  };

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    backgroundColor: folder.color,
  };

  const pickerColors = FOLDER_COLORS.slice(0, 5);

  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      {...attributes} 
      {...listeners}
      className="rounded-[32px] shadow-card p-6 flex flex-col gap-3 relative group"
    >
      <div className="flex items-center justify-between mb-3 px-2">
        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={tempTitle}
            onChange={(e) => setTempTitle(e.target.value)}
            onBlur={handleRenameSubmit}
            onKeyDown={(e) => e.key === 'Enter' && handleRenameSubmit()}
            className="bg-white/50 rounded-lg px-2 py-1 text-xs font-bold text-black outline-none w-full"
          />
        ) : (
          <span 
            onDoubleClick={(e) => {
              e.stopPropagation();
              setEditing(true);
            }}
            className="text-xs font-bold text-black/40 uppercase tracking-wider cursor-text"
          >
            {folder.title || 'Dossier'}
          </span>
        )}
      </div>

      <div className="absolute -top-2 -right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity z-20">
        <button 
          onClick={(e) => {
            e.stopPropagation();
            setEditing(true);
          }}
          className="w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center hover:bg-blue-50"
          title="Renommer le dossier"
        >
          <Edit2 className="w-4 h-4 text-blue-500" />
        </button>
        <div className="relative" ref={pickerRef}>
          <button 
            onClick={(e) => {
              e.stopPropagation();
              setShowColorPicker(!showColorPicker);
            }}
            className="w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center hover:bg-gray-50"
            title="Changer la couleur"
          >
            <div className="w-4 h-4 rounded-full border border-black/10" style={{ backgroundColor: folder.color }} />
          </button>

          <AnimatePresence>
            {showColorPicker && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 5 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 5 }}
                className="absolute top-10 right-0 bg-white rounded-2xl shadow-xl p-3 flex gap-2 border border-black/5"
              >
                {pickerColors.map((color) => (
                  <button
                    key={color}
                    onClick={(e) => {
                      e.stopPropagation();
                      onColorChange(folder.id, color);
                      setShowColorPicker(false);
                    }}
                    className={`w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 ${folder.color === color ? 'border-black' : 'border-transparent'}`}
                    style={{ backgroundColor: color }}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onFolderDelete(folder.id);
          }}
          className="w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center hover:bg-red-50"
        >
          <X className="w-4 h-4 text-red-500" />
        </button>
      </div>

      <SortableContext items={pages.map(p => p.id)} strategy={verticalListSortingStrategy}>
        {pages.map((page) => (
          <div key={page.id}>
            <SortablePageItem 
              page={page} 
              onDelete={onPageDelete}
              onClick={onPageClick}
            />
          </div>
        ))}
      </SortableContext>
      
      {pages.length === 0 && (
        <div className="py-8 flex flex-col items-center justify-center text-black/20 border-2 border-dashed border-black/10 rounded-2xl">
          <Plus className="w-6 h-6 mb-2" />
          <span className="text-xs font-medium">Déposer une page ici</span>
        </div>
      )}
    </div>
  );
}

// --- Main App ---

export default function App() {
  const [view, setView] = useState<View>('home');
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedTrashIds, setSelectedTrashIds] = useState<string[]>([]);

  const [pages, setPages] = useState<Page[]>([
    { id: 'p1', title: 'Idées vidéos', content: '', isDeleted: false, folderId: null },
    { id: 'p2', title: 'Phrases de maman', content: '', isDeleted: false, folderId: null },
    { id: 'p3', title: 'Pourquoi pas en vr...', content: '', isDeleted: false, folderId: null },
    { id: 'p4', title: 'Jsp', content: '', isDeleted: false, folderId: null },
    { id: 'p5', title: 'Action 5', content: '', isDeleted: false, folderId: null },
    { id: 'p6', title: 'Action 6', content: '', isDeleted: false, folderId: null },
    { id: 'p7', title: 'Action 7', content: '', isDeleted: false, folderId: null },
    // Folder pages
    { id: 'p8', title: 'Vidéos', content: '', isDeleted: false, folderId: 'f1' },
    { id: 'p9', title: 'Tournage', content: '', isDeleted: false, folderId: 'f1' },
    { id: 'p10', title: 'Drive', content: '', isDeleted: false, folderId: 'f1' },
    { id: 'p11', title: 'Youtube', content: '', isDeleted: false, folderId: 'f1' },
    { id: 'p12', title: 'Tournage', content: '', isDeleted: false, folderId: 'f2' },
    { id: 'p13', title: 'Drive', content: '', isDeleted: false, folderId: 'f2' },
    { id: 'p14', title: 'Youtube', content: '', isDeleted: false, folderId: 'f2' },
    { id: 'p15', title: 'Vidéos', content: '', isDeleted: false, folderId: 'f3' },
    { id: 'p16', title: 'Tournage', content: '', isDeleted: false, folderId: 'f3' },
    { id: 'p17', title: 'Vidéos', content: '', isDeleted: false, folderId: 'f4' },
    { id: 'p18', title: 'Tournage', content: '', isDeleted: false, folderId: 'f4' },
    { id: 'p19', title: 'Drive', content: '', isDeleted: false, folderId: 'f4' },
    { id: 'p20', title: 'Youtube', content: '', isDeleted: false, folderId: 'f4' },
  ]);

  const [folders, setFolders] = useState<Folder[]>([
    { id: 'f1', color: '#C9F0FD', title: 'Vidéos' },
    { id: 'f2', color: '#D9F0D9', title: 'Projets' },
    { id: 'f3', color: '#FDC9C9', title: 'Perso' },
    { id: 'f4', color: '#FDC9FD', title: 'Social' },
  ]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // --- Derived State ---

  const activePage = useMemo(() => pages.find(p => p.id === selectedPageId), [pages, selectedPageId]);

  const filteredPages = useMemo(() => {
    const query = searchQuery.toLowerCase();
    return pages.filter(p => 
      !p.isDeleted && 
      (p.title.toLowerCase().includes(query) || p.content.toLowerCase().includes(query))
    );
  }, [pages, searchQuery]);

  const trashPages = useMemo(() => pages.filter(p => p.isDeleted), [pages]);

  const allTrashSelected = useMemo(() => 
    trashPages.length > 0 && selectedTrashIds.length === trashPages.length,
    [trashPages, selectedTrashIds]
  );

  const homePages = useMemo(() => filteredPages.filter(p => p.folderId === null), [filteredPages]);

  // --- Handlers ---

  const handleAddPage = () => {
    const newId = `p${Date.now()}`;
    const newPage: Page = {
      id: newId,
      title: 'Nouvelle page',
      content: '',
      isDeleted: false,
      folderId: null,
    };
    setPages(prev => [newPage, ...prev]);
  };

  const handlePageDelete = (id: string) => {
    if (view === 'trash') {
      setPages(prev => prev.filter(p => p.id !== id));
    } else {
      setPages(prev => prev.map(p => p.id === id ? { ...p, isDeleted: true, folderId: null } : p));
    }
  };

  const handleRestorePage = (id: string) => {
    setPages(prev => prev.map(p => p.id === id ? { ...p, isDeleted: false } : p));
  };

  const handleToggleTrashSelection = (id: string) => {
    setSelectedTrashIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleSelectAllTrash = () => {
    if (allTrashSelected) {
      setSelectedTrashIds([]);
    } else {
      setSelectedTrashIds(trashPages.map(p => p.id));
    }
  };

  const handleDeleteSelectedTrash = () => {
    setPages(prev => prev.filter(p => !selectedTrashIds.includes(p.id)));
    setSelectedTrashIds([]);
  };

  const handleAddFolder = () => {
    const usedColors = folders.map(f => f.color);
    const availableColors = FOLDER_COLORS.filter(c => !usedColors.includes(c));
    const color = availableColors.length > 0 ? availableColors[0] : FOLDER_COLORS[Math.floor(Math.random() * FOLDER_COLORS.length)];
    
    const newFolder: Folder = {
      id: `f${Date.now()}`,
      color,
      title: 'Nouveau Dossier',
    };
    setFolders(prev => [...prev, newFolder]);
  };

  const handleFolderDelete = (id: string) => {
    setFolders(prev => prev.filter(f => f.id !== id));
    setPages(prev => prev.map(p => p.folderId === id ? { ...p, folderId: null } : p));
  };

  const handleFolderRename = (id: string, newTitle: string) => {
    setFolders(prev => prev.map(f => f.id === id ? { ...f, title: newTitle } : f));
  };

  const handleColorChange = (id: string, color: string) => {
    setFolders(prev => prev.map(f => {
      if (f.id === id) {
        return { ...f, color };
      }
      return f;
    }));
  };

  const handlePageClick = (page: Page) => {
    setSelectedPageId(page.id);
    setView('detail');
  };

  const handleBack = () => {
    setView('home');
    setSelectedPageId(null);
  };

  // --- Drag & Drop Handlers ---

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // If dragging a page over a folder or another page in a folder
    const activePage = pages.find(p => p.id === activeId);
    if (!activePage) return;

    const overFolder = folders.find(f => f.id === overId);
    const overPage = pages.find(p => p.id === overId);

    if (overFolder) {
      if (activePage.folderId !== overFolder.id) {
        setPages(prev => prev.map(p => p.id === activeId ? { ...p, folderId: overFolder.id } : p));
      }
    } else if (overPage && overPage.folderId) {
      if (activePage.folderId !== overPage.folderId) {
        setPages(prev => prev.map(p => p.id === activeId ? { ...p, folderId: overPage.folderId } : p));
      }
    } else if (overId === 'page-column') {
      if (activePage.folderId !== null) {
        setPages(prev => prev.map(p => p.id === activeId ? { ...p, folderId: null } : p));
      }
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    if (activeId === overId) return;

    // Handle Folder Reordering
    const activeFolderIndex = folders.findIndex(f => f.id === activeId);
    const overFolderIndex = folders.findIndex(f => f.id === overId);

    if (activeFolderIndex !== -1 && overFolderIndex !== -1) {
      setFolders(prev => arrayMove(prev, activeFolderIndex, overFolderIndex));
      return;
    }

    // Handle Page Reordering within same context
    const activePageIndex = pages.findIndex(p => p.id === activeId);
    const overPageIndex = pages.findIndex(p => p.id === overId);

    if (activePageIndex !== -1 && overPageIndex !== -1) {
      const activePage = pages[activePageIndex];
      const overPage = pages[overPageIndex];

      if (activePage.folderId === overPage.folderId) {
        setPages(prev => arrayMove(prev, activePageIndex, overPageIndex));
      }
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center p-6 overflow-x-hidden relative">
      {/* Top Navigation */}
      <nav className="flex gap-12 mb-12 text-[#8E8E93] text-sm font-medium items-center">
        <button 
          onClick={() => setView('home')}
          className={`transition-colors ${view === 'home' ? 'text-black' : 'hover:text-black'}`}
        >
          Accueil
        </button>
        <button 
          onClick={() => setView('trash')}
          className={`transition-colors ${view === 'trash' ? 'text-black' : 'hover:text-black'}`}
        >
          Poubelle
        </button>
        
        {/* Search Bar */}
        <div className="relative flex items-center group">
          <Search className={`w-4 h-4 absolute left-0 transition-colors ${searchQuery ? 'text-black' : 'text-[#8E8E93]'}`} />
          <input
            type="text"
            placeholder="Chercher"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-6 bg-transparent outline-none text-sm font-medium text-black placeholder-[#8E8E93] w-24 focus:w-48 transition-all"
          />
        </div>
      </nav>

      <AnimatePresence mode="wait">
        {view === 'home' || view === 'trash' ? (
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="w-full max-w-7xl flex flex-col items-center mt-8"
          >
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDragEnd={handleDragEnd}
              modifiers={[restrictToWindowEdges]}
            >
              <div className={`w-full ${view === 'trash' ? 'flex flex-col items-center' : 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-16'} px-6 items-start`}>
                
                {/* Page Column */}
                <div className={`flex flex-col items-center ${view === 'trash' ? 'w-full max-w-6xl' : 'w-full'}`}>
                  <div className="w-full flex justify-center items-center mb-6 relative">
                    <span className="text-[#8E8E93] text-sm font-medium">
                      {view === 'trash' ? 'Poubelle' : 'Page'}
                    </span>
                    
                    {view === 'trash' && trashPages.length > 0 && (
                      <div className="absolute right-0 flex items-center gap-4">
                        <button 
                          onClick={handleSelectAllTrash}
                          className="flex items-center gap-2 text-sm font-medium text-[#8E8E93] hover:text-black transition-colors"
                        >
                          <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${allTrashSelected ? 'bg-black border-black text-white' : 'border-black/10 bg-white'}`}>
                            {allTrashSelected && <Check className="w-3 h-3" strokeWidth={3} />}
                          </div>
                          Tout sélectionner
                        </button>
                        
                        {selectedTrashIds.length > 0 && (
                          <button 
                            onClick={handleDeleteSelectedTrash}
                            className="flex items-center gap-2 px-4 py-2 rounded-full bg-red-500 text-white text-xs font-bold hover:bg-red-600 transition-colors shadow-lg shadow-red-500/20"
                          >
                            <Trash2 className="w-3 h-3" />
                            Supprimer ({selectedTrashIds.length})
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {view === 'home' && (
                    <button 
                      onClick={handleAddPage}
                      className="w-16 h-16 rounded-full bg-[#FDFDC9] shadow-soft flex items-center justify-center mb-6 hover:scale-105 transition-transform"
                    >
                      <Plus className="w-6 h-6 text-black" strokeWidth={2.5} />
                    </button>
                  )}
                  
                  <div 
                    id="page-column"
                    className={`w-full bg-white rounded-[32px] shadow-card p-6 min-h-[200px] ${
                      view === 'trash' 
                        ? 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4' 
                        : 'flex flex-col gap-3'
                    }`}
                  >
                      <SortableContext 
                        items={view === 'trash' ? trashPages.map(p => p.id) : homePages.map(p => p.id)} 
                        strategy={view === 'trash' ? rectSortingStrategy : verticalListSortingStrategy}
                      >
                        {(view === 'trash' ? trashPages : homePages).map((page) => (
                          <div key={page.id}>
                            <SortablePageItem 
                              page={page} 
                              onDelete={handlePageDelete}
                              onRestore={view === 'trash' ? handleRestorePage : undefined}
                              onClick={handlePageClick}
                              selected={selectedTrashIds.includes(page.id)}
                              onToggleSelection={view === 'trash' ? () => handleToggleTrashSelection(page.id) : undefined}
                            />
                          </div>
                        ))}
                      </SortableContext>
                    
                    {(view === 'trash' ? trashPages : homePages).length === 0 && (
                      <div className="flex flex-col items-center justify-center py-12 text-[#8E8E93]/30">
                        {view === 'trash' ? <Trash2 className="w-8 h-8 mb-2" /> : <Edit2 className="w-8 h-8 mb-2" />}
                        <span className="text-xs font-medium">Vide</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Dossier Column */}
                {view === 'home' && (
                  <div className="flex flex-col items-center lg:col-span-2">
                    <span className="text-[#8E8E93] text-sm font-medium mb-6">Dossier</span>
                    <button 
                      onClick={handleAddFolder}
                      className="w-16 h-16 rounded-full bg-white shadow-soft flex items-center justify-center mb-6 hover:scale-105 transition-transform"
                    >
                      <Plus className="w-6 h-6 text-black" strokeWidth={2.5} />
                    </button>

                    <div className="flex flex-col sm:flex-row gap-6 w-full items-start">
                      <SortableContext items={folders.map(f => f.id)} strategy={verticalListSortingStrategy}>
                        <div className="flex flex-col gap-6 flex-1 w-full">
                          {folders.filter((_, i) => i % 2 === 0).map((folder) => (
                            <div key={folder.id}>
                              <SortableFolder
                                folder={folder}
                                pages={filteredPages.filter(p => p.folderId === folder.id)}
                                onPageDelete={handlePageDelete}
                                onPageClick={handlePageClick}
                                onFolderDelete={handleFolderDelete}
                                onFolderRename={handleFolderRename}
                                onColorChange={handleColorChange}
                              />
                            </div>
                          ))}
                        </div>
                        <div className="flex flex-col gap-6 flex-1 w-full">
                          {folders.filter((_, i) => i % 2 !== 0).map((folder) => (
                            <div key={folder.id}>
                              <SortableFolder
                                folder={folder}
                                pages={filteredPages.filter(p => p.folderId === folder.id)}
                                onPageDelete={handlePageDelete}
                                onPageClick={handlePageClick}
                                onFolderDelete={handleFolderDelete}
                                onFolderRename={handleFolderRename}
                                onColorChange={handleColorChange}
                              />
                            </div>
                          ))}
                        </div>
                      </SortableContext>
                    </div>
                  </div>
                )}
              </div>

              <DragOverlay dropAnimation={{
                sideEffects: defaultDropAnimationSideEffects({
                  styles: {
                    active: {
                      opacity: '0.5',
                    },
                  },
                }),
              }}>
                {activeId ? (
                  activeId.startsWith('p') ? (
                    <div className="w-[272px]">
                      <PillItem 
                        label={pages.find(p => p.id === activeId)?.title || ''} 
                        variant={pages.find(p => p.id === activeId)?.title === 'Idées vidéos' ? 'red' : 'default'}
                        selected={selectedTrashIds.includes(activeId)}
                        onToggleSelection={view === 'trash' ? () => {} : undefined}
                      />
                    </div>
                  ) : (
                    <div 
                      className="w-[320px] rounded-[32px] shadow-card p-6 flex flex-col gap-3"
                      style={{ backgroundColor: folders.find(f => f.id === activeId)?.color }}
                    >
                      <div className="flex items-center px-2 mb-1">
                        <span className="text-xs font-bold text-black/40 uppercase tracking-wider">
                          {folders.find(f => f.id === activeId)?.title || 'Dossier'}
                        </span>
                      </div>
                      {filteredPages.filter(p => p.folderId === activeId).map((page, idx) => (
                        <div key={idx}>
                          <PillItem label={page.title} />
                        </div>
                      ))}
                    </div>
                  )
                ) : null}
              </DragOverlay>
            </DndContext>
          </motion.div>
        ) : (
          <motion.div
            key="detail"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-6xl px-4"
          >
            <div className="bg-white rounded-[40px] shadow-card p-12 min-h-[600px]">
              <div className="flex items-center gap-6 mb-12">
                <button 
                  onClick={handleBack}
                  className="w-10 h-10 rounded-full bg-[#FDC9C9] flex items-center justify-center hover:scale-110 transition-transform"
                >
                  <ChevronLeft className="w-5 h-5 text-black" strokeWidth={2.5} />
                </button>
                <input
                  type="text"
                  className="text-3xl font-bold text-black bg-transparent outline-none w-full"
                  value={activePage?.title || ''}
                  onChange={(e) => {
                    if (selectedPageId) {
                      setPages(prev => prev.map(p => p.id === selectedPageId ? { ...p, title: e.target.value } : p));
                    }
                  }}
                />
              </div>
              
              <textarea 
                className="w-full h-full min-h-[400px] text-xl text-[#8E8E93] outline-none resize-none bg-transparent"
                placeholder="Écrire ici..."
                value={activePage?.content || ''}
                onChange={(e) => {
                  if (selectedPageId) {
                    setPages(prev => prev.map(p => p.id === selectedPageId ? { ...p, content: e.target.value } : p));
                  }
                }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="mt-auto pt-12 pb-4 flex items-center gap-3">
        <Logo onClick={() => setView('home')} className="relative opacity-50" size="24" />
        <p className="text-[#8E8E93] text-xs font-medium">
          Fishe App for searching anything and write everything - Build By Tobias
        </p>
      </footer>
    </div>
  );
}
