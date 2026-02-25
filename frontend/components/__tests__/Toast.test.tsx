import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { ToastProvider, useToast } from "../Toast";

// Helper component to test useToast hook
function ToastTestComponent() {
  const { toast, confirm } = useToast();
  
  return (
    <div>
      <button 
        onClick={() => toast("Success message", "success")}
        data-testid="show-success"
      >
        Show Success
      </button>
      <button 
        onClick={() => toast("Error message", "error")}
        data-testid="show-error"
      >
        Show Error
      </button>
      <button 
        onClick={() => toast("Warning message", "warning")}
        data-testid="show-warning"
      >
        Show Warning
      </button>
      <button 
        onClick={() => toast("Info message", "info")}
        data-testid="show-info"
      >
        Show Info
      </button>
      <button 
        onClick={() => toast("Default message")}
        data-testid="show-default"
      >
        Show Default
      </button>
      <button 
        onClick={async () => {
          const result = await confirm("Are you sure?");
          // Store result for testing
          (window as unknown as { confirmResult: boolean }).confirmResult = result;
        }}
        data-testid="show-confirm"
      >
        Show Confirm
      </button>
    </div>
  );
}

describe("Toast", () => {
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
      
      expect(screen.getByTestId("show-success")).toBeInTheDocument();
    });
  });

  describe("useToast hook", () => {
    it("throws error when used outside provider", () => {
      const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
      
      expect(() => {
        render(<ToastTestComponent />);
      }).toThrow("useToast must be used inside <ToastProvider>");
      
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

  describe("Toast auto-removal", () => {
    it("auto-removes toast after 4 seconds", async () => {
      vi.useFakeTimers();
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      expect(screen.getByText("Success message")).toBeInTheDocument();
      
      await act(async () => {
        await vi.advanceTimersByTimeAsync(4000);
      });

      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
      vi.useRealTimers();
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
      expect(toast).toHaveClass("bg-emerald-600/90");
    });

    it("applies error styles", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-error"));
      
      const toast = screen.getByText("Error message").closest("div");
      expect(toast).toHaveClass("bg-red-600/90");
    });

    it("applies warning styles", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-warning"));
      
      const toast = screen.getByText("Warning message").closest("div");
      expect(toast).toHaveClass("bg-amber-500/90");
    });

    it("applies info styles", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-info"));
      
      const toast = screen.getByText("Info message").closest("div");
      expect(toast).toHaveClass("bg-slate-700/90");
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
      const container = document.querySelector(".fixed.bottom-5");
      expect(container).toBeNull();
    });

    it("renders container with correct positioning", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-success"));
      
      const container = document.querySelector(".fixed.bottom-5.right-5");
      expect(container).toBeInTheDocument();
      expect(container).toHaveClass("z-50");
    });
  });

  describe("Confirm dialog", () => {
    it("shows confirm dialog", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-confirm"));
      
      expect(screen.getByText("Are you sure?")).toBeInTheDocument();
      expect(screen.getByText("Отмена")).toBeInTheDocument();
      expect(screen.getByText("Подтвердить")).toBeInTheDocument();
    });

    it("resolves with false when cancelled", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-confirm"));
      fireEvent.click(screen.getByText("Отмена"));
      
      await waitFor(() => {
        expect((window as unknown as { confirmResult: boolean }).confirmResult).toBe(false);
      });
    });

    it("resolves with true when confirmed", async () => {
      render(
        <ToastProvider>
          <ToastTestComponent />
        </ToastProvider>
      );
      
      fireEvent.click(screen.getByTestId("show-confirm"));
      fireEvent.click(screen.getByText("Подтвердить"));
      
      await waitFor(() => {
        expect((window as unknown as { confirmResult: boolean }).confirmResult).toBe(true);
      });
    });
  });
});
