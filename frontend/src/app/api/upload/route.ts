import { NextResponse } from "next/server";

export const runtime = "nodejs"; // Changed to nodejs to support crypto module

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
        // Now using nodejs runtime, so we can use crypto module.
        // So we simulate a file upload with a UUID.

        const { randomUUID } = await import("crypto");
        const simulatedFileId = randomUUID();

        return NextResponse.json({ fileId: simulatedFileId });
    } catch (err: any) {
        return NextResponse.json(
            { error: "Upload failed", message: err.message },
            { status: 500 }
        );
    }
}
