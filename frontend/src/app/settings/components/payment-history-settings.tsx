"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FileText, Download, DollarSign, ChevronLeft, ChevronRight, CheckCircle2, XCircle } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api-client";
import { registerAuthenticatedCacheClearer } from "@/lib/auth-cache";

interface PaymentHistoryItem {
  id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  description: string | null;
  invoice_url: string | null;
  receipt_url: string | null;
}

interface PaymentStats {
  total_spent: number;
  total_payments: number;
  successful_payments: number;
  failed_payments: number;
  pending_payments: number;
  refunded_payments: number;
  currency: string;
}

const PAGE_SIZE = 10;
const PAYMENT_HISTORY_CACHE_TTL_MS = 30_000;
const PAYMENT_HISTORY_CACHE_MAX_ENTRIES = 12;
let paymentHistoryCacheGeneration = 0;

type PaymentHistoryCacheEntry = {
  payments: PaymentHistoryItem[];
  total: number;
  timestamp: number;
};

const paymentStatsCache: {
  value: PaymentStats | null;
  timestamp: number;
} = {
  value: null,
  timestamp: 0,
};

const paymentHistoryCache = new Map<string, PaymentHistoryCacheEntry>();
let paymentStatsPromise: Promise<PaymentStats> | null = null;
const paymentHistoryPromises = new Map<string, Promise<{ payments: PaymentHistoryItem[]; total: number }>>();

function hasFreshCache(timestamp: number): boolean {
  return timestamp > 0 && Date.now() - timestamp < PAYMENT_HISTORY_CACHE_TTL_MS;
}

function pruneHistoryCache(): void {
  for (const [key, value] of paymentHistoryCache.entries()) {
    if (!hasFreshCache(value.timestamp)) {
      paymentHistoryCache.delete(key);
    }
  }

  while (paymentHistoryCache.size > PAYMENT_HISTORY_CACHE_MAX_ENTRIES) {
    const oldestKey = paymentHistoryCache.keys().next().value;
    if (!oldestKey) {
      break;
    }
    paymentHistoryCache.delete(oldestKey);
  }
}

function getHistoryCacheKey(page: number, statusFilter: string): string {
  return `${page}:${statusFilter}`;
}

export function clearPaymentHistoryCache(): void {
  paymentStatsCache.value = null;
  paymentStatsCache.timestamp = 0;
  paymentHistoryCache.clear();
  paymentStatsPromise = null;
  paymentHistoryPromises.clear();
  paymentHistoryCacheGeneration += 1;
}

export function __clearPaymentHistoryCacheForTests(): void {
  clearPaymentHistoryCache();
}

registerAuthenticatedCacheClearer(clearPaymentHistoryCache);

export function PaymentHistorySettings() {
  const [paymentHistory, setPaymentHistory] = useState<PaymentHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'succeeded' | 'failed'>('all');
  const historyRequestIdRef = useRef(0);
  const statsRequestIdRef = useRef(0);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  
  // Stats from API (aggregated - accurate across all pages)
  const [stats, setStats] = useState<PaymentStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const requestStats = useCallback(async () => {
    if (paymentStatsPromise) {
      return paymentStatsPromise;
    }

    const cacheGeneration = paymentHistoryCacheGeneration;
    const requestPromise = apiClient.get("/payment/history/stats")
      .then(({ data }) => {
        if (cacheGeneration === paymentHistoryCacheGeneration) {
          paymentStatsCache.value = data;
          paymentStatsCache.timestamp = Date.now();
        }
        return data;
      })
      .finally(() => {
        if (paymentStatsPromise === requestPromise) {
          paymentStatsPromise = null;
        }
      });

    paymentStatsPromise = requestPromise;
    return requestPromise;
  }, []);

  const requestPaymentHistory = useCallback(async (page: number, statusFilter: string) => {
    const cacheKey = getHistoryCacheKey(page, statusFilter);
    const existingPromise = paymentHistoryPromises.get(cacheKey);
    if (existingPromise) {
      return existingPromise;
    }

    const offset = (page - 1) * PAGE_SIZE;
    const params: Record<string, unknown> = { limit: PAGE_SIZE, offset };
    if (statusFilter !== "all") {
      params.status = statusFilter;
    }

    const cacheGeneration = paymentHistoryCacheGeneration;
    const requestPromise = apiClient
      .get("/payment/history", { params })
      .then(({ data }) => {
        const result = {
          payments: data?.payments ?? [],
          total: data?.total ?? data?.payments?.length ?? 0,
        };
        if (cacheGeneration === paymentHistoryCacheGeneration) {
          paymentHistoryCache.set(cacheKey, {
            ...result,
            timestamp: Date.now(),
          });
          pruneHistoryCache();
        }
        return result;
      })
      .finally(() => {
        if (paymentHistoryPromises.get(cacheKey) === requestPromise) {
          paymentHistoryPromises.delete(cacheKey);
        }
      });

    paymentHistoryPromises.set(cacheKey, requestPromise);
    return requestPromise;
  }, []);

  // Fetch aggregated stats from dedicated API
  const fetchStats = useCallback(async () => {
    if (paymentStatsCache.value && hasFreshCache(paymentStatsCache.timestamp)) {
      setStats(paymentStatsCache.value);
      setStatsLoading(false);
      return;
    }

    const cacheGeneration = paymentHistoryCacheGeneration;
    const requestId = statsRequestIdRef.current + 1;
    statsRequestIdRef.current = requestId;
    setStatsLoading(true);
    try {
      const data = await requestStats();
      if (
        requestId !== statsRequestIdRef.current ||
        cacheGeneration !== paymentHistoryCacheGeneration
      ) {
        return;
      }
      setStats(data);
    } catch {
      // Error state handled through UI
    } finally {
      if (
        requestId === statsRequestIdRef.current &&
        cacheGeneration === paymentHistoryCacheGeneration
      ) {
        setStatsLoading(false);
      }
    }
  }, [requestStats]);

  // Fetch payment history with pagination and server-side filtering
  const fetchPaymentHistory = useCallback(async (page: number, statusFilter: string) => {
    pruneHistoryCache();
    const cacheKey = getHistoryCacheKey(page, statusFilter);
    const cachedHistory = paymentHistoryCache.get(cacheKey);

    if (cachedHistory && hasFreshCache(cachedHistory.timestamp)) {
      setPaymentHistory(cachedHistory.payments);
      setTotalCount(cachedHistory.total);
      setHistoryLoading(false);
      return;
    }

    const cacheGeneration = paymentHistoryCacheGeneration;
    const requestId = historyRequestIdRef.current + 1;
    historyRequestIdRef.current = requestId;
    setHistoryLoading(true);
    try {
      const data = await requestPaymentHistory(page, statusFilter);
      if (
        requestId !== historyRequestIdRef.current ||
        cacheGeneration !== paymentHistoryCacheGeneration
      ) {
        return;
      }
      setPaymentHistory(data.payments);
      setTotalCount(data.total);
    } catch {
      // Error state handled through UI
    } finally {
      if (
        requestId === historyRequestIdRef.current &&
        cacheGeneration === paymentHistoryCacheGeneration
      ) {
        setHistoryLoading(false);
      }
    }
  }, [requestPaymentHistory]);

  // Initial load - fetch both stats and history
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Fetch history when page or filter changes
  useEffect(() => {
    fetchPaymentHistory(currentPage, filter);
  }, [currentPage, filter, fetchPaymentHistory]);

  // Reset to page 1 when filter changes
  const handleFilterChange = useCallback((newFilter: 'all' | 'succeeded' | 'failed') => {
    setFilter(newFilter);
    setCurrentPage(1);  // Reset pagination when filter changes
  }, []);

  // Pagination calculations
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const canGoBack = currentPage > 1;
  const canGoForward = currentPage < totalPages;

  // Use stats from API (accurate across all pages)
  const totalSpent = stats?.total_spent ?? 0;
  const successCount = stats?.successful_payments ?? 0;
  const failedCount = stats?.failed_payments ?? 0;

  const formatCurrency = (amount: number, currency: string) => {
    return amount.toLocaleString('en-US', { 
      style: 'currency', 
      currency: currency.toUpperCase() 
    });
  };

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-border bg-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/10">
                <DollarSign className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Spent</p>
                <div className="text-xl font-bold text-foreground">
                  {statsLoading ? (
                    <Skeleton className="h-7 w-24" />
                  ) : (
                    formatCurrency(totalSpent, stats?.currency ?? 'usd')
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <CheckCircle2 className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Successful Payments</p>
                <div className="text-xl font-bold text-foreground">
                  {statsLoading ? <Skeleton className="h-7 w-12" /> : successCount}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <XCircle className="h-5 w-5 text-red-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Failed Payments</p>
                <div className="text-xl font-bold text-foreground">
                  {statsLoading ? <Skeleton className="h-7 w-12" /> : failedCount}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payment History Table */}
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
              <FileText className="h-5 w-5 text-purple-500" />
              Transaction History
            </CardTitle>
            
            {/* Filter Buttons */}
            <div className="flex items-center gap-2">
              <div className="flex gap-1 bg-muted/50 rounded-lg p-1">
                {(['all', 'succeeded', 'failed'] as const).map((f) => (
                  <Button
                    key={f}
                    variant={filter === f ? "default" : "ghost"}
                    size="sm"
                    onClick={() => handleFilterChange(f)}
                    className={`text-xs px-3 ${filter === f ? '' : 'hover:bg-muted'}`}
                  >
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex justify-between items-center p-4 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-24" />
                    </div>
                  </div>
                  <Skeleton className="h-6 w-20" />
                </div>
              ))}
            </div>
          ) : paymentHistory.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-16 w-16 mx-auto opacity-20 mb-4" />
              <p className="text-lg font-medium">No payment history</p>
              <p className="text-sm mt-1">
                {filter === 'all' 
                  ? "You haven't made any payments yet." 
                  : `No ${filter} payments found.`
                }
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50 hover:bg-muted/50">
                    <TableHead className="font-semibold">Date</TableHead>
                    <TableHead className="font-semibold">Description</TableHead>
                    <TableHead className="font-semibold">Amount</TableHead>
                    <TableHead className="font-semibold">Status</TableHead>
                    <TableHead className="text-right font-semibold">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paymentHistory.map((item) => (
                    <TableRow key={item.id} className="group">
                      <TableCell className="font-medium">
                        <div className="flex flex-col">
                          <span>{new Date(item.created_at).toLocaleDateString('en-GB')}</span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(item.created_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground max-w-[250px]">
                        <span className="line-clamp-2">{item.description ?? 'Payment'}</span>
                      </TableCell>
                      <TableCell>
                        <span className={`font-bold ${item.status === 'succeeded' ? 'text-foreground' : 'text-muted-foreground'}`}>
                          {formatCurrency(item.amount, item.currency)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge className={`
                          ${item.status === 'succeeded' 
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' 
                            : item.status === 'failed' 
                              ? 'bg-red-500/10 text-red-500 border-red-500/20' 
                              : 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                          } border
                        `}>
                          {item.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          {item.invoice_url && (
                            <Button 
                              variant="outline" 
                              size="sm" 
                              asChild 
                              className="h-8 px-3 text-xs"
                            >
                              <a href={item.invoice_url} target="_blank" rel="noopener noreferrer">
                                <FileText className="h-3 w-3 mr-1" />
                                Invoice
                              </a>
                            </Button>
                          )}
                          {item.receipt_url && (
                            <Button 
                              variant="outline" 
                              size="sm" 
                              asChild 
                              className="h-8 px-3 text-xs"
                            >
                              <a href={item.receipt_url} target="_blank" rel="noopener noreferrer">
                                <Download className="h-3 w-3 mr-1" />
                                Receipt
                              </a>
                            </Button>
                          )}
                          {!item.invoice_url && !item.receipt_url && (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          
          {/* Pagination Controls */}
          {totalPages > 1 && !historyLoading && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                Page {currentPage} of {totalPages} ({totalCount} total records)
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => p - 1)}
                  disabled={!canGoBack}
                  className="h-8"
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => p + 1)}
                  disabled={!canGoForward}
                  className="h-8"
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
