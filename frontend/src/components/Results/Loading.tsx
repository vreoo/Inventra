import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export function Loading() {
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const messages = [
    "Analyzing historical data patterns",
    "Computing forecast variables",
    "Applying machine learning models",
    "Generating insights",
    "Preparing results",
  ];

  useEffect(() => {
    // Progress animation
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 0.5;
      });
    }, 50);

    // Message rotation
    const messageInterval = setInterval(() => {
      setMessage((prev) => {
        const currentIndex = messages.indexOf(prev);
        return messages[(currentIndex + 1) % messages.length];
      });
    }, 3000);

    // Set initial message
    setMessage(messages[0]);

    return () => {
      clearInterval(progressInterval);
      clearInterval(messageInterval);
    };
  }, []);

  return (
    <div className="flex items-center justify-center min-h-[400px] p-4">
      <Card className="w-[400px]">
        <CardHeader>
          <CardTitle className="text-center">Generating Forecast</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <Progress value={progress} className="h-2" />
            <p className="text-center text-sm text-muted-foreground">
              {message}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
