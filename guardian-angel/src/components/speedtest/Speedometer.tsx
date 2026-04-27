import React, { useEffect, useRef } from 'react';

interface SpeedometerProps {
    value: number;
    max: number;
    label: string;
    phase: 'idle' | 'ping' | 'download' | 'upload';
    size?: number;
}

export const Speedometer = ({ value, max, label, phase, size = 300 }: SpeedometerProps) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const requestRef = useRef<number>();
    const currentValueRef = useRef(0);

    // Speedometer configuration
    const startAngle = Math.PI * 0.8;
    const endAngle = Math.PI * 2.2;
    const radius = size * 0.4;
    const center = size / 2;

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const animate = () => {
            // Smooth interpolation
            const diff = value - currentValueRef.current;
            currentValueRef.current += diff * 0.1;

            ctx.clearRect(0, 0, size, size);

            // Draw Background Arc
            ctx.beginPath();
            ctx.arc(center, center, radius, startAngle, endAngle);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.lineWidth = 15;
            ctx.lineCap = 'round';
            ctx.stroke();

            // Draw Ticks
            for (let i = 0; i <= 10; i++) {
                const angle = startAngle + (endAngle - startAngle) * (i / 10);
                const innerR = radius - 20;
                const outerR = radius - 5;

                const x1 = center + Math.cos(angle) * innerR;
                const y1 = center + Math.sin(angle) * innerR;
                const x2 = center + Math.cos(angle) * outerR;
                const y2 = center + Math.sin(angle) * outerR;

                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Draw Progress Arc
            const progressRatio = Math.min(Math.max(currentValueRef.current, 0), max) / max;
            const currentAngle = startAngle + (endAngle - startAngle) * progressRatio;

            // Gradient for progress
            const gradient = ctx.createLinearGradient(0, 0, size, 0);
            if (phase === 'upload') {
                gradient.addColorStop(0, '#3b82f6'); // Blue
                gradient.addColorStop(1, '#8b5cf6'); // Purple
            } else {
                gradient.addColorStop(0, '#06b6d4'); // Cyan
                gradient.addColorStop(1, '#10b981'); // Emerald
            }

            if (currentValueRef.current > 0) {
                ctx.beginPath();
                ctx.arc(center, center, radius, startAngle, currentAngle);
                ctx.strokeStyle = gradient;
                ctx.lineWidth = 15;
                ctx.lineCap = 'round';

                // Add glow
                ctx.shadowBlur = 15;
                ctx.shadowColor = phase === 'upload' ? '#3b82f6' : '#06b6d4';

                ctx.stroke();
                ctx.shadowBlur = 0; // Reset shadow
            }

            // Draw Needle
            const needleAngle = currentAngle;
            const needleLength = radius - 30;
            const needleX = center + Math.cos(needleAngle) * needleLength;
            const needleY = center + Math.sin(needleAngle) * needleLength;

            ctx.beginPath();
            ctx.moveTo(center, center);
            ctx.lineTo(needleX, needleY);
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 3;
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#fff';
            ctx.stroke();
            ctx.shadowBlur = 0;

            // Center Pivot
            ctx.beginPath();
            ctx.arc(center, center, 8, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.fill();

            requestRef.current = requestAnimationFrame(animate);
        };

        requestRef.current = requestAnimationFrame(animate);

        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [value, max, phase, size]);

    return (
        <div className="relative flex flex-col items-center justify-center">
            <canvas
                ref={canvasRef}
                width={size}
                height={size}
                className="max-w-full h-auto"
            />
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 translate-y-8 text-center">
                <div className="text-4xl font-bold font-mono tracking-tighter text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]">
                    {value.toFixed(1)}
                </div>
                <div className="text-sm font-medium text-muted-foreground uppercase tracking-wider mt-1">
                    {label}
                </div>
            </div>
        </div>
    );
};
