import { useEffect, useState } from "react";

export function Loading() {
    const [dots, setDots] = useState("");
    const [message, setMessage] = useState("");
    const messages = [
        "Discovering trends",
        "Analyzing patterns",
        "Processing data",
        "Creating Predictions",
        "Generating insights",
        "Almost there",
    ];

    useEffect(() => {
        // Animate the dots
        const dotInterval = setInterval(() => {
            setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
        }, 500);

        // Cycle through messages
        const messageInterval = setInterval(() => {
            setMessage((prev) => {
                const currentIndex = messages.indexOf(prev);
                return messages[(currentIndex + 1) % messages.length];
            });
        }, 3000);

        // Set initial message
        setMessage(messages[0]);

        return () => {
            clearInterval(dotInterval);
            clearInterval(messageInterval);
        };
    }, []);

    return (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-8">
            <div className="relative">
                <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                    <div className="h-12 w-12 rounded-full bg-blue-100 opacity-50"></div>
                </div>
            </div>
            <div className="mt-4 text-center">
                <p className="text-lg text-gray-700 font-medium">
                    {message}
                    <span className="font-mono">{dots}</span>
                </p>
                <p className="text-sm text-gray-500 mt-2">
                    This may take a few moments
                </p>
            </div>
        </div>
    );
}
