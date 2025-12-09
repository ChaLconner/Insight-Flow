"use client";

import React, { useState, useCallback, useMemo, memo } from 'react';
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { AnalyticsPeriod } from "@/types";
import { BurndownDataPoint } from "@/app/analytics/types";
import { CustomSelect } from "@/components/ui/custom-select";
import { motion, AnimatePresence } from "framer-motion";

// Import charts
import { BurndownChart } from "./BurndownChart";
import { WorkloadChart } from "./WorkloadChart";
import { CreationCompletionChart } from "./CreationCompletionChart";
import { StatusDistributionChart } from "./StatusDistributionChart";
import { PriorityChart } from "./PriorityChart";
import { ChartErrorBoundary } from "./ChartErrorBoundary";

interface ChartCarouselProps {
    burndownData: BurndownDataPoint[];
    workloadData: { name: string; avatar?: string; tasks: number }[];
    dailyTrendsData: { date: string; created: number; completed: number }[];
    statusDistribution: { name: string; value: number }[];
    priorityDistribution: { name: string; value: number }[];

    period: AnalyticsPeriod;
    setPeriod: (value: AnalyticsPeriod) => void;
}

// Period options moved outside component to prevent recreation
const PERIOD_OPTIONS = [
    { value: AnalyticsPeriod.WEEK, label: "This Week" },
    { value: AnalyticsPeriod.MONTH, label: "This Month" },
    { value: AnalyticsPeriod.QUARTER, label: "This Quarter" },
    { value: AnalyticsPeriod.YEAR, label: "This Year" },
];

// Animation variants moved outside component
const SLIDE_VARIANTS = {
    enter: (direction: number) => ({
        x: direction > 0 ? "100%" : "-100%",
        opacity: 0
    }),
    center: {
        zIndex: 1,
        x: 0,
        opacity: 1
    },
    exit: (direction: number) => ({
        zIndex: 0,
        x: direction < 0 ? "100%" : "-100%",
        opacity: 0
    })
} as const;

const SLIDE_TRANSITION = {
    x: { type: "spring", stiffness: 300, damping: 30 },
    opacity: { duration: 0.2 }
} as const;

const ChartCarouselComponent: React.FC<ChartCarouselProps> = ({
    burndownData,
    workloadData,
    dailyTrendsData,
    statusDistribution,
    priorityDistribution,
    period,
    setPeriod
}) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [direction, setDirection] = useState(0);

    // Memoize charts array to prevent recreation on each render
    const charts = useMemo(() => [
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Progress Chart Error">
                    <BurndownChart data={burndownData} period={period} />
                </ChartErrorBoundary>
            ),
            key: 'burndown'
        },
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Workload Chart Error">
                    <WorkloadChart data={workloadData} />
                </ChartErrorBoundary>
            ),
            key: 'workload'
        },
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Trends Chart Error">
                    <CreationCompletionChart data={dailyTrendsData} />
                </ChartErrorBoundary>
            ),
            key: 'creation-completion'
        },
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Status Distribution Error">
                    <StatusDistributionChart data={statusDistribution} />
                </ChartErrorBoundary>
            ),
            key: 'status-distribution'
        },
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Priority Chart Error">
                    <PriorityChart data={priorityDistribution} />
                </ChartErrorBoundary>
            ),
            key: 'priority-distribution'
        }
    ], [burndownData, workloadData, dailyTrendsData, statusDistribution, priorityDistribution, period]);

    // Memoize navigation handlers
    const nextSlide = useCallback(() => {
        setDirection(1);
        setCurrentIndex((prev) => (prev + 1) % charts.length);
    }, [charts.length]);

    const prevSlide = useCallback(() => {
        setDirection(-1);
        setCurrentIndex((prev) => (prev - 1 + charts.length) % charts.length);
    }, [charts.length]);

    // Memoize pagination click handler
    const handlePaginationClick = useCallback((index: number) => {
        setDirection(index > currentIndex ? 1 : -1);
        setCurrentIndex(index);
    }, [currentIndex]);

    // Memoize period change handler
    const handlePeriodChange = useCallback((value: string) => {
        setPeriod(value as AnalyticsPeriod);
    }, [setPeriod]);

    return (
        <div className="relative group pb-8">
            {/* Period Selector */}
            <div className="absolute top-4 right-4 z-20 w-[160px]">
                <CustomSelect
                    value={period}
                    onChange={handlePeriodChange}
                    options={PERIOD_OPTIONS}
                    size="sm"
                />
            </div>

            {/* Carousel Viewport */}
            <div className="relative h-[450px] overflow-hidden rounded-xl border border-white/5 bg-white/5 backdrop-blur-sm">
                <AnimatePresence initial={false} custom={direction} mode="popLayout">
                    <motion.div
                        key={currentIndex}
                        custom={direction}
                        variants={SLIDE_VARIANTS}
                        initial="enter"
                        animate="center"
                        exit="exit"
                        transition={SLIDE_TRANSITION}
                        className="absolute w-full h-full"
                    >
                        <div className="h-full w-full">
                            {charts[currentIndex].component}
                        </div>
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Navigation Buttons */}
            <div className="absolute top-[200px] -translate-y-1/2 left-0 z-20 opacity-0 group-hover:opacity-100 transition-opacity pl-2">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={prevSlide}
                    className="h-10 w-10 sm:h-12 sm:w-12 rounded-full bg-black/40 hover:bg-black/60 text-white backdrop-blur-sm border border-white/10"
                >
                    <ChevronLeft className="h-6 w-6" />
                </Button>
            </div>

            <div className="absolute top-[200px] -translate-y-1/2 right-0 z-20 opacity-0 group-hover:opacity-100 transition-opacity pr-2">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={nextSlide}
                    className="h-10 w-10 sm:h-12 sm:w-12 rounded-full bg-black/40 hover:bg-black/60 text-white backdrop-blur-sm border border-white/10"
                >
                    <ChevronRight className="h-6 w-6" />
                </Button>
            </div>

            {/* Pagination Indicators */}
            <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 flex gap-2">
                {charts.map((_, index) => (
                    <button
                        key={index}
                        onClick={() => handlePaginationClick(index)}
                        className={`h-2 w-2 rounded-full transition-all ${index === currentIndex
                            ? "bg-indigo-500 w-4"
                            : "bg-zinc-600 hover:bg-zinc-500"
                            }`}
                        aria-label={`Go to slide ${index + 1}`}
                    />
                ))}
            </div>
        </div>
    );
};

// Export with memo for performance optimization
export const ChartCarousel = memo(ChartCarouselComponent);
