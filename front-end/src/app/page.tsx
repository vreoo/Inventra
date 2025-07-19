import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function Home() {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
            <Link href="/upload">
                <Button asChild>
                    <span>Go to Upload Page</span>
                </Button>
            </Link>
        </div>
    );
}
