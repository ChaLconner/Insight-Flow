import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { Search, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { usersApi } from "@/lib/api-endpoints";
import type { User as UserType } from "@/types";
import { getAvatarUrl } from "@/lib/utils";

interface UserSearchSelectProps {
  value: string;
  onChange: (value: string) => void;
  onUserSelect?: (user: UserType) => void;
  className?: string;
  placeholder?: string;
}

export function UserSearchSelect({
  value,
  onChange,
  onUserSelect,
  className,
  placeholder,
}: UserSearchSelectProps) {
  const [query, setQuery] = useState(value);
  const [users, setUsers] = useState<UserType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSearch = (searchTerm: string) => {
    setQuery(searchTerm);
    onChange(searchTerm); // Update form value as user types

    if (searchTerm.length < 2) {
      setUsers([]);
      setIsOpen(false);
      return;
    }

    setIsLoading(true);
    setIsOpen(true);

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const results = await usersApi.searchUsers(searchTerm);
        setUsers(Array.isArray(results) ? results : []);
      } catch (error) {
        console.error("Search failed:", error);
        setUsers([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);
  };

  const handleSelect = (user: UserType) => {
    if (onUserSelect) {
      onUserSelect(user);
    } else {
      setQuery(user.email);
      onChange(user.email);
    }
    setIsOpen(false);
  };

  return (
    <div className={cn("relative", className)} ref={containerRef}>
      <div className="relative">
        <Input
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder={placeholder}
          className="pl-10"
        />
        {isLoading ? (
          <Loader2 className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin text-zinc-400" />
        ) : (
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
        )}
      </div>

      {isOpen && users.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-white/10 bg-zinc-900/95 backdrop-blur-xl shadow-xl max-h-60 overflow-auto custom-scrollbar">
          {users.map((user) => (
            <button
              key={user.id}
              onClick={() => handleSelect(user)}
              className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-white/10 transition-colors cursor-pointer"
            >
              <div className="relative h-8 w-8 rounded-full bg-zinc-800 overflow-hidden flex items-center justify-center shrink-0">
                {user.avatar ? (
                  <Image
                    src={getAvatarUrl(user.avatar)}
                    alt={user.username}
                    fill
                    className="object-cover"
                    sizes="32px"
                  />
                ) : (
                  <span className="text-xs font-medium text-zinc-400">
                    {user.firstName?.[0]}
                    {user.lastName?.[0]}
                  </span>
                )}
              </div>
              <div className="flex flex-col overflow-hidden">
                <span className="text-sm font-medium text-white truncate">
                  {user.firstName} {user.lastName}{" "}
                  <span className="text-zinc-500 text-xs">
                    (@{user.username})
                  </span>
                </span>
                <span className="text-xs text-zinc-400 truncate">
                  {user.email}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {isOpen && query.length >= 2 && !isLoading && users.length === 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-white/10 bg-zinc-900/95 backdrop-blur-xl shadow-xl p-3 text-sm text-zinc-400 text-center">
          No matching users found
        </div>
      )}
    </div>
  );
}
