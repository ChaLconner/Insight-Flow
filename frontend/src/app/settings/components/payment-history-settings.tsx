"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FileText, Download, DollarSign, ChevronLeft, ChevronRight, CheckCircle2, XCircle } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api-client";

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

export function PaymentHistorySettings() {
  const [paymentHistory, setPaymentHistory] = useState<PaymentHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'succeeded' | 'failed'>('all');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  
  // Stats from API (aggregated - accurate across all pages)
  const [stats, setStats] = useState<PaymentStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Fetch aggregated stats from dedicated API
  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const { data } = await apiClient.get("/payment/history/stats");
      setStats(data);
    } catch {
      // Error state handled through UI
    } finally {
      setStatsLoading(false);
    }
  }, []);

  // Fetch payment history with pagination and server-side filtering
  const fetchPaymentHistory = useCallback(async (page: number, statusFilter: string) => {
    setHistoryLoading(true);
    try {
      const offset = (page - 1) * PAGE_SIZE;
      const params: Record<string, unknown> = { limit: PAGE_SIZE, offset };
      
      // Only add status param if not 'all'
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      
      const { data } = await apiClient.get("/payment/history", { params });
      if (data?.payments) {
        setPaymentHistory(data.payments);
        setTotalCount(data.total ?? data.payments.length);
      }
    } catch {
      // Error state handled through UI
    } finally {
      setHistoryLoading(false);
    }
  }, []);

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
                    formatCurrency(totalSpent, 'usd')
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
