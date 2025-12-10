"use client";

import { Suspense, lazy, useState, useCallback, useMemo, memo } from 'react';
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { AnalyticsPeriod } from "@/types";
import { BurndownDataPoint, TeamWorkloadPaginatedResponse, TeamWorkloadParams } from "@/app/analytics/types";
import { CustomSelect } from "@/components/ui/custom-select";
import { motion, AnimatePresence } from "framer-motion";

// Import charts - Keep BurndownChart eager for specific LCP optimization
import { BurndownChart } from "./BurndownChart";

// Lazy load secondary charts
const WorkloadChart = lazy(() => import("./WorkloadChart").then(mod => ({ default: mod.WorkloadChart })));
const CreationCompletionChart = lazy(() => import("./CreationCompletionChart").then(mod => ({ default: mod.CreationCompletionChart })));
const StatusDistributionChart = lazy(() => import("./StatusDistributionChart").then(mod => ({ default: mod.StatusDistributionChart })));
const PriorityChart = lazy(() => import("./PriorityChart").then(mod => ({ default: mod.PriorityChart })));

import { ChartErrorBoundary } from "./ChartErrorBoundary";

interface ChartCarouselProps {
    burndownData: BurndownDataPoint[];
    workloadData: { name: string; avatar?: string; tasks: number }[];
    dailyTrendsData: { date: string; created: number; completed: number }[];
    statusDistribution: { name: string; value: number }[];
    priorityDistribution: { name: string; value: number }[];

    period: AnalyticsPeriod;
    setPeriod: (value: AnalyticsPeriod) => void;

    // Pagination support for large team workload (1K-100K users)
    usePaginatedWorkload?: boolean;
    paginatedWorkloadData?: TeamWorkloadPaginatedResponse | null;
    onWorkloadPageChange?: (params: TeamWorkloadParams) => void;
    isWorkloadLoading?: boolean;
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

const ChartLoadingFallback = () => (
    <div className="flex h-full w-full items-center justify-center bg-white/5 rounded-xl border border-white/10">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
    </div>
);

const ChartCarouselComponent: React.FC<ChartCarouselProps> = ({
    burndownData,
    workloadData,
    dailyTrendsData,
    statusDistribution,
    priorityDistribution,
    period,
    setPeriod,
    usePaginatedWorkload = false,
    paginatedWorkloadData,
    onWorkloadPageChange,
    isWorkloadLoading = false
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
                    <Suspense fallback={<ChartLoadingFallback />}>
                        <WorkloadChart
                            data={workloadData}
                            usePagination={usePaginatedWorkload}
                            paginatedData={paginatedWorkloadData}
                            onPageChange={onWorkloadPageChange}
                            isLoading={isWorkloadLoading}
                        />
                    </Suspense>
                </ChartErrorBoundary>
            ),
            key: 'workload'
        },
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Trends Chart Error">
                    <Suspense fallback={<ChartLoadingFallback />}>
                        <CreationCompletionChart data={dailyTrendsData} />
                    </Suspense>
                </ChartErrorBoundary>
            ),
            key: 'creation-completion'
        },
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Status Distribution Error">
                    <Suspense fallback={<ChartLoadingFallback />}>
                        <StatusDistributionChart data={statusDistribution} />
                    </Suspense>
                </ChartErrorBoundary>
            ),
            key: 'status-distribution'
        },
        {
            component: (
                <ChartErrorBoundary fallbackTitle="Priority Chart Error">
                    <Suspense fallback={<ChartLoadingFallback />}>
                        <PriorityChart data={priorityDistribution} />
                    </Suspense>
                </ChartErrorBoundary>
            ),
            key: 'priority-distribution'
        }
    ], [burndownData, workloadData, dailyTrendsData, statusDistribution, priorityDistribution, period, usePaginatedWorkload, paginatedWorkloadData, onWorkloadPageChange, isWorkloadLoading]);

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
            {/* Period Selector - Moved outside to prevent overlap with chart headers */}
            <div className="flex justify-end pb-2 px-1 z-10 relative">
                <div className="w-[160px]">
                    <CustomSelect
                        value={period}
                        onChange={handlePeriodChange}
                        options={PERIOD_OPTIONS}
                        size="sm"
                    />
                </div>
            </div>

            {/* Carousel Viewport */}
            <div className="relative h-[450px] overflow-hidden rounded-xl">

                {/* Left Navigation Zone */}
                <div
                    className="absolute top-24 bottom-12 left-0 w-12 z-10 cursor-pointer flex items-center justify-center text-white/30 hover:text-white hover:bg-white/5 transition-all"
                    onClick={(e) => {
                        e.stopPropagation();
                        prevSlide();
                    }}
                    role="button"
                    aria-label="Previous slide"
                >
                    <ChevronLeft className="h-8 w-8" />
                </div>

                {/* Right Navigation Zone */}
                <div
                    className="absolute top-24 bottom-12 right-0 w-12 z-10 cursor-pointer flex items-center justify-center text-white/30 hover:text-white hover:bg-white/5 transition-all"
                    onClick={(e) => {
                        e.stopPropagation();
                        nextSlide();
                    }}
                    role="button"
                    aria-label="Next slide"
                >
                    <ChevronRight className="h-8 w-8" />
                </div>

                <AnimatePresence initial={false} custom={direction} mode="popLayout">
                    <motion.div
                        key={currentIndex}
                        custom={direction}
                        variants={SLIDE_VARIANTS}
                        initial="enter"
                        animate="center"
                        exit="exit"
                        transition={SLIDE_TRANSITION}
                        drag="x"
                        dragConstraints={{ left: 0, right: 0 }}
                        dragElastic={1}
                        onDragEnd={(e, { offset, velocity }) => {
                            const swipe = Math.abs(offset.x) * velocity.x;
                            const swipeConfidenceThreshold = 10000;

                            if (swipe < -swipeConfidenceThreshold) {
                                nextSlide();
                            } else if (swipe > swipeConfidenceThreshold) {
                                prevSlide();
                            }
                        }}
                        className="absolute w-full h-full cursor-grab active:cursor-grabbing"
                    >
                        <div className="h-full w-full">
                            {charts[currentIndex].component}
                        </div>
                    </motion.div>
                </AnimatePresence>
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
