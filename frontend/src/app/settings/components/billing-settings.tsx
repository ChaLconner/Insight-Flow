"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function BillingSettings() {
  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white">
            Current Plan
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
            <div>
              <h3 className="text-lg font-semibold text-white">Pro Plan</h3>
              <p className="text-zinc-400">$29/month • Billed monthly</p>
              <p className="text-sm text-zinc-500 mt-1">
                Next billing: February 18, 2024
              </p>
            </div>
            <Badge className="bg-emerald-500/20 text-emerald-400">Active</Badge>
          </div>

          <div className="flex gap-3">
            <Button variant="glass">Change Plan</Button>
            <Button variant="glass">Cancel Subscription</Button>
          </div>
        </CardContent>
      </Card>

      {/* Usage */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white">
            Usage This Month
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-zinc-400">Projects</span>
              <span className="text-white">3 / 10</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-indigo-500 w-[30%]" />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-zinc-400">Storage</span>
              <span className="text-white">2.4 GB / 10 GB</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-blue-500 w-[24%]" />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-zinc-400">Team Members</span>
              <span className="text-white">6 / 25</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-emerald-500 w-[24%]" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payment Method */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white">
            Payment Method
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
            <div className="flex items-center gap-3">
              <div className="h-8 w-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded flex items-center justify-center">
                <span className="text-white text-xs font-bold">VISA</span>
              </div>
              <div>
                <p className="text-white font-medium">•••• •••• •••• 4242</p>
                <p className="text-zinc-400 text-sm">Expires 12/26</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="border border-white/10 text-white bg-transparent hover:bg-white/10"
            >
              Update
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
