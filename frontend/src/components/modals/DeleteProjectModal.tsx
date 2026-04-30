"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertTriangle } from "lucide-react";
import type { Project } from "@/types";
import { useState, useEffect } from "react";
import { AnimatedModalShell } from "./AnimatedModalShell";

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
    <AnimatedModalShell
      isOpen={isOpen}
      onClose={onClose}
      className="relative w-full max-w-md rounded-2xl border border-border bg-popover/95 backdrop-blur-xl shadow-2xl overflow-hidden"
    >
            <div className="p-6 space-y-6">
              <div className="flex flex-col items-center text-center gap-4">
                <div className="h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center text-red-500">
                  <AlertTriangle className="h-6 w-6" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold text-foreground">
                    Delete Project
                  </h3>
                  <p className="text-muted-foreground">
                    This action cannot be undone. This will permanently delete
                    the project{" "}
                    <span className="text-foreground font-medium">
                      "{project?.name}"
                    </span>{" "}
                    and remove all associated tasks, members, and data.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <label htmlFor="delete-project-confirm" className="text-xs font-medium text-muted-foreground uppercase">
                  Type{" "}
                  <span className="text-foreground selectable select-all">
                    {project?.name}
                  </span>{" "}
                  to confirm
                </label>
                <Input
                  id="delete-project-confirm"
                  name="confirmName"
                  value={confirmName}
                  onChange={(e) => setConfirmName(e.target.value)}
                  placeholder={project?.name}
                  className="bg-background border-border text-foreground placeholder:text-muted-foreground/50"
                  autoComplete="off"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                  className="flex-1 text-muted-foreground hover:text-foreground hover:bg-accent"
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
    </AnimatedModalShell>
  );
}
