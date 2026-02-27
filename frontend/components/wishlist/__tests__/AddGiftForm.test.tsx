import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import AddGiftForm from "../AddGiftForm";
import { ToastProvider } from "../../Toast";

const wishlist = {
  id: 1,
  slug: "test",
  title: "Test",
  owner_id: 1,
  gifts: [],
};

describe("AddGiftForm image upload", () => {
  it("shows error for unsupported file type", () => {
    render(
      <ToastProvider>
        <AddGiftForm wishlist={wishlist as any} onRefetch={() => {}} />
      </ToastProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Загрузить файл" }));

    const input = screen.getByLabelText("Загрузить изображение") as HTMLInputElement;
    expect(input.type).toBe("file");

    const file = new File(["hello"], "test.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText("Поддерживаются только JPEG, PNG или WebP.")).toBeInTheDocument();
  });

  it("shows error for file larger than 5MB", () => {
    render(
      <ToastProvider>
        <AddGiftForm wishlist={wishlist as any} onRefetch={() => {}} />
      </ToastProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Загрузить файл" }));

    const input = screen.getByLabelText("Загрузить изображение") as HTMLInputElement;
    expect(input.type).toBe("file");

    const bytes = new Uint8Array(5 * 1024 * 1024 + 1);
    const file = new File([bytes], "big.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText("Размер файла не должен превышать 5 МБ.")).toBeInTheDocument();
  });
});
