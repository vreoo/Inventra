import { NextResponse } from "next/server";
import { randomUUID } from "crypto";

export const runtime = "edge"; // Optional: Use "nodejs" if using fs module

export async function POST(req: Request) {
    try {
        const contentType = req.headers.get("content-type") || "";
        if (!contentType.includes("multipart/form-data")) {
            return NextResponse.json(
                { error: "Invalid content type" },
                { status: 400 }
            );
        }

        // This is a placeholder — in real usage you'd use formidable, busboy, etc.
        // But in Edge runtime, file parsing is limited.
        // So we simulate a file upload with a UUID.

        const simulatedFileId = randomUUID();

        return NextResponse.json({ fileId: simulatedFileId });
    } catch (err: any) {
        return NextResponse.json(
            { error: "Upload failed", message: err.message },
            { status: 500 }
        );
    }
}
