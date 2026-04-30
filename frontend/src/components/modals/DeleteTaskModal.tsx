"use client";

import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import type { Task } from "@/types";
import { AnimatedModalShell } from "./AnimatedModalShell";

interface DeleteTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  task: Task | null;
  isDeleting: boolean;
}

export function DeleteTaskModal({
  isOpen,
  onClose,
  onConfirm,
  task,
  isDeleting,
}: DeleteTaskModalProps) {
  return (
    <AnimatedModalShell
      isOpen={isOpen}
      onClose={onClose}
      className="relative w-full max-w-md rounded-2xl border border-border bg-popover/95 backdrop-blur-xl shadow-2xl overflow-hidden"
    >
            <div className="p-6 space-y-6">
              <div className="flex flex-col items-center text-center gap-4">
                <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center text-destructive">
                  <Trash2 className="h-6 w-6" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold text-foreground">
                    Delete Task
                  </h3>
                  <p className="text-muted-foreground">
                    Are you sure you want to delete{" "}
                    <span className="text-foreground font-medium">
                      "{task?.title}"
                    </span>
                    ? This action cannot be undone.
                  </p>
                </div>
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
                  className="flex-1 bg-destructive hover:bg-destructive/90"
                  disabled={isDeleting}
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </Button>
              </div>
            </div>
    </AnimatedModalShell>
  );
}
