"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertTriangle } from "lucide-react";
import type { Project } from "@/types";
import { useState, useEffect } from "react";

interface DeleteProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  project: Project | null;
  isDeleting: boolean;
}

export function DeleteProjectModal({
  isOpen,
  onClose,
  onConfirm,
  project,
  isDeleting,
}: DeleteProjectModalProps) {
  const [confirmName, setConfirmName] = useState("");

  // Reset input when modal opens
  useEffect(() => {
    if (isOpen) {
      setConfirmName("");
    }
  }, [isOpen]);

  const isConfirmed = confirmName === project?.name;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-md rounded-2xl border border-white/10 bg-[#18181b]/95 backdrop-blur-xl shadow-2xl overflow-hidden"
          >
            <div className="p-6 space-y-6">
              <div className="flex flex-col items-center text-center gap-4">
                <div className="h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center text-red-500">
                  <AlertTriangle className="h-6 w-6" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold text-white">
                    Delete Project
                  </h3>
                  <p className="text-zinc-400">
                    This action cannot be undone. This will permanently delete
                    the project{" "}
                    <span className="text-white font-medium">
                      "{project?.name}"
                    </span>{" "}
                    and remove all associated tasks, members, and data.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-xs font-medium text-zinc-400 uppercase">
                  Type{" "}
                  <span className="text-zinc-300 selectable select-all">
                    {project?.name}
                  </span>{" "}
                  to confirm
                </label>
                <Input
                  value={confirmName}
                  onChange={(e) => setConfirmName(e.target.value)}
                  placeholder={project?.name}
                  className="bg-zinc-900/50 border-white/10 text-white placeholder:text-zinc-600"
                  autoComplete="off"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                  className="flex-1 text-zinc-400 hover:text-white hover:bg-white/10"
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={onConfirm}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
                  disabled={!isConfirmed || isDeleting}
                >
                  {isDeleting ? "Deleting..." : "Delete Project"}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
