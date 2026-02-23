import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { ToastProvider, useToast } from "../Toast";

// Helper component to test useToast hook
function ToastTestComponent() {
  const { showToast, removeToast, toasts } = useToast();
  
  return (
    <div>
      <span data-testid="toast-count">{toasts.length}</span>
      <button 
        onClick={() => showToast("Success message", "success")}
        data-testid="show-success"
      >
        Show Success
      </button>
      <button 
        onClick={() => showToast("Error message", "error")}
        data-testid="show-error"
      >
        Show Error
      </button>
      <button 
        onClick={() => showToast("Warning message", "warning")}
        data-testid="show-warning"
      >
        Show Warning
      </button>
      <button 
        onClick={() => showToast("Info message", "info")}
        data-testid="show-info"
      >
        Show Info
      </button>
      <button 
        onClick={() => showToast("Default message")}
        data-testid="show-default"
      >
        Show Default
      </button>
      {toasts.length > 0 && (
        <button 
          onClick={() => removeToast(toasts[0].id)}
          data-testid="remove-first"
        >
          Remove First
        </button>
      )}
    </div>
  );
}

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe("ToastProvider", () => {
    it("renders children", () => {
      render(
        <ToastProvider>
          <div>Child content</div>
        </ToastProvider>
      );
      
      expect(screen.getByText("Child content")).toBeInTheDocument();
    });

    it("provides toast context", () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      expect(screen.getByTestId("toast-count")).toHaveTextContent("0");
    });
  });

  describe("useToast hook", () => {
    it("throws error when used outside provider", () => {
      const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
      
      expect(() => {
        render(<ToastTestComponent />);
      }).toThrow("useToast must be used within ToastProvider");
      
      consoleError.mockRestore();
    });

    it("shows success toast", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      
      expect(screen.getByText("Success message")).toBeInTheDocument();
      expect(screen.getByTestId("toast-count")).toHaveTextContent("1");
    });

    it("shows error toast", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-error"));
      
      expect(screen.getByText("Error message")).toBeInTheDocument();
    });

    it("shows warning toast", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-warning"));
      
      expect(screen.getByText("Warning message")).toBeInTheDocument();
    });

    it("shows info toast", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-info"));
      
      expect(screen.getByText("Info message")).toBeInTheDocument();
    });

    it("shows toast with default type (info)", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-default"));
      
      expect(screen.getByText("Default message")).toBeInTheDocument();
    });
  });

  describe("Toast removal", () => {
    it("removes toast manually", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      expect(screen.getByText("Success message")).toBeInTheDocument();
      
      fireEvent.click(screen.getByTestId("remove-first"));
      
      await waitFor(() => {
        expect(screen.queryByText("Success message")).not.toBeInTheDocument();
      });
    });

    it("auto-removes toast after 4 seconds", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      expect(screen.getByText("Success message")).toBeInTheDocument();
      
      act(() => {
        vi.advanceTimersByTime(4000);
      });
      
      await waitFor(() => {
        expect(screen.queryByText("Success message")).not.toBeInTheDocument();
      });
    });

    it("removes toast via close button", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      
      const closeButton = screen.getByRole("button", { name: "" });
      fireEvent.click(closeButton);
      
      await waitFor(() => {
        expect(screen.queryByText("Success message")).not.toBeInTheDocument();
      });
    });
  });

  describe("Multiple toasts", () => {
    it("shows multiple toasts", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      fireEvent.click(screen.getByTestId("show-error"));
      fireEvent.click(screen.getByTestId("show-warning"));
      
      expect(screen.getByText("Success message")).toBeInTheDocument();
      expect(screen.getByText("Error message")).toBeInTheDocument();
      expect(screen.getByText("Warning message")).toBeInTheDocument();
      expect(screen.getByTestId("toast-count")).toHaveTextContent("3");
    });

    it("removes correct toast when multiple exist", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      fireEvent.click(screen.getByTestId("show-error"));
      
      expect(screen.getByText("Success message")).toBeInTheDocument();
      expect(screen.getByText("Error message")).toBeInTheDocument();
      
      fireEvent.click(screen.getByTestId("remove-first"));
      
      await waitFor(() => {
        expect(screen.queryByText("Success message")).not.toBeInTheDocument();
        expect(screen.getByText("Error message")).toBeInTheDocument();
      });
    });
  });

  describe("Toast styling", () => {
    it("applies success styles", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      
      const toast = screen.getByText("Success message").closest("div");
      expect(toast).toHaveClass("bg-emerald-600/95");
    });

    it("applies error styles", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-error"));
      
      const toast = screen.getByText("Error message").closest("div");
      expect(toast).toHaveClass("bg-red-600/95");
    });

    it("applies warning styles", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-warning"));
      
      const toast = screen.getByText("Warning message").closest("div");
      expect(toast).toHaveClass("bg-amber-500/95");
    });

    it("applies info styles", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-info"));
      
      const toast = screen.getByText("Info message").closest("div");
      expect(toast).toHaveClass("bg-slate-700/95");
    });
  });

  describe("Toast icons", () => {
    it("renders success icon for success toast", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      
      // Check for checkmark path in SVG
      const svg = document.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("renders error icon for error toast", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-error"));
      
      const svg = document.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });
  });

  describe("Toast container", () => {
    it("does not render container when no toasts", () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      // Container should not be rendered
      const container = document.querySelector(".fixed.bottom-4");
      expect(container).toBeNull();
    });

    it("renders container with correct positioning", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      
      const container = document.querySelector(".fixed.bottom-4.right-4");
      expect(container).toBeInTheDocument();
      expect(container).toHaveClass("z-50");
    });
  });
});
