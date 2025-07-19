import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function GET(
    req: NextRequest,
    context: { params: { id: string } }
) {
    const { id } = context.params;

    // Simulated job tracking and result
    const mockResults = {
        jobId: id,
        status: "COMPLETED",
        results: {
            stockoutDate: "2025-08-12",
            reorderPoint: 35,
            peakSeason: "Q4",
            insights: [
                "Inventory trend increasing in Q3",
                "Projected stockout within 24 days",
                "Reorder advised on August 5",
            ],
        },
    };

    return NextResponse.json(mockResults);
}
