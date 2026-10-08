import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const FILE = path.join(process.cwd(), "data", "flags.json");

export async function GET() {
  try {
    return NextResponse.json(JSON.parse(await fs.readFile(FILE, "utf8")));
  } catch {
    return NextResponse.json([]);
  }
}

export async function POST(req: Request) {
  try {
    await fs.mkdir(path.dirname(FILE), { recursive: true });
    await fs.writeFile(FILE, JSON.stringify(await req.json()));
    return NextResponse.json({ ok: true });
  } catch (err: any) {
    return NextResponse.json({ ok: false, error: err?.message }, { status: 500 });
  }
}
