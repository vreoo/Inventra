import { NextResponse } from "next/server";
import { randomUUID } from "crypto";

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { fileId, config } = body;

        if (!fileId || !config) {
            return NextResponse.json(
                { error: "Missing fileId or config" },
                { status: 400 }
            );
        }

        // Simulate creating a forecast job
        const jobId = randomUUID();

        return NextResponse.json({ jobId });
    } catch (err: any) {
        return NextResponse.json(
            { error: "Failed to create forecast job", message: err.message },
            { status: 500 }
        );
    }
}
