import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfirmModal } from "../ConfirmModal";

describe("ConfirmModal", () => {
  const defaultProps = {
    isOpen: true,
    title: "Подтверждение",
    message: "Вы уверены?",
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  describe("Rendering", () => {
    it("renders when open", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      expect(screen.getByText("Подтверждение")).toBeInTheDocument();
      expect(screen.getByText("Вы уверены?")).toBeInTheDocument();
    });

    it("does not render when closed", () => {
      render(<ConfirmModal {...defaultProps} isOpen={false} />);
      
      expect(screen.queryByText("Подтверждение")).not.toBeInTheDocument();
      expect(screen.queryByText("Вы уверены?")).not.toBeInTheDocument();
    });

    it("renders default confirm button text", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      expect(screen.getByText("Подтвердить")).toBeInTheDocument();
    });

    it("renders default cancel button text", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      expect(screen.getByText("Отмена")).toBeInTheDocument();
    });

    it("renders custom confirm button text", () => {
      render(
        <ConfirmModal 
          {...defaultProps} 
          confirmText="Удалить" 
        />
      );
      
      expect(screen.getByText("Удалить")).toBeInTheDocument();
    });

    it("renders custom cancel button text", () => {
      render(
        <ConfirmModal 
          {...defaultProps} 
          cancelText="Закрыть" 
        />
      );
      
      expect(screen.getByText("Закрыть")).toBeInTheDocument();
    });
  });

  describe("Variants", () => {
    it("renders danger variant by default", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      const confirmButton = screen.getByText("Подтвердить");
      expect(confirmButton).toHaveClass("bg-red-600");
    });

    it("renders danger variant explicitly", () => {
      render(
        <ConfirmModal 
          {...defaultProps} 
          confirmVariant="danger" 
        />
      );
      
      const confirmButton = screen.getByText("Подтвердить");
      expect(confirmButton).toHaveClass("bg-red-600");
    });

    it("renders primary variant", () => {
      render(
        <ConfirmModal 
          {...defaultProps} 
          confirmVariant="primary" 
        />
      );
      
      const confirmButton = screen.getByText("Подтвердить");
      expect(confirmButton).toHaveClass("btn-primary");
    });
  });

  describe("Interactions", () => {
    it("calls onConfirm when confirm button clicked", () => {
      const onConfirm = vi.fn();
      render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />);
      
      fireEvent.click(screen.getByText("Подтвердить"));
      
      expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it("calls onCancel when cancel button clicked", () => {
      const onCancel = vi.fn();
      render(<ConfirmModal {...defaultProps} onCancel={onCancel} />);
      
      fireEvent.click(screen.getByText("Отмена"));
      
      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it("calls onCancel when backdrop clicked", () => {
      const onCancel = vi.fn();
      render(<ConfirmModal {...defaultProps} onCancel={onCancel} />);
      
      // Find backdrop by class
      const backdrop = document.querySelector(".bg-black\\/60");
      fireEvent.click(backdrop!);
      
      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it("does not call onConfirm when backdrop clicked", () => {
      const onConfirm = vi.fn();
      render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />);
      
      const backdrop = document.querySelector(".bg-black\\/60");
      fireEvent.click(backdrop!);
      
      expect(onConfirm).not.toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("has proper heading structure", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      const heading = screen.getByRole("heading", { level: 3 });
      expect(heading).toHaveTextContent("Подтверждение");
    });

    it("has buttons with accessible names", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      expect(screen.getByRole("button", { name: "Подтвердить" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Отмена" })).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("has backdrop with blur effect", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      const backdrop = document.querySelector(".backdrop-blur-sm");
      expect(backdrop).toBeInTheDocument();
    });

    it("has modal with animation class", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      const modal = document.querySelector(".animate-scale-in");
      expect(modal).toBeInTheDocument();
    });

    it("has proper z-index for overlay", () => {
      render(<ConfirmModal {...defaultProps} />);
      
      const overlay = document.querySelector(".z-50");
      expect(overlay).toBeInTheDocument();
    });
  });

  describe("Edge cases", () => {
    it("handles empty title", () => {
      render(<ConfirmModal {...defaultProps} title="" />);
      
      expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    });

    it("handles empty message", () => {
      render(<ConfirmModal {...defaultProps} message="" />);
      
      // Modal should still render
      expect(screen.getByText("Подтвердить")).toBeInTheDocument();
    });

    it("handles long title", () => {
      const longTitle = "Очень длинный заголовок для проверки того, как компонент обрабатывает длинный текст";
      render(<ConfirmModal {...defaultProps} title={longTitle} />);
      
      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });

    it("handles long message", () => {
      const longMessage = "Очень длинное сообщение для проверки того, как компонент обрабатывает длинный текст сообщения";
      render(<ConfirmModal {...defaultProps} message={longMessage} />);
      
      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it("handles special characters in text", () => {
      render(
        <ConfirmModal 
          {...defaultProps} 
          title="Удалить элемент?" 
          message="Это действие нельзя отменить! Спецсимволы: <>&quot;"
        />
      );
      
      expect(screen.getByText(/Удалить/)).toBeInTheDocument();
      expect(screen.getByText(/Спецсимволы/)).toBeInTheDocument();
    });
  });

  describe("Multiple modals scenario", () => {
    it("renders multiple modals independently", () => {
      const { rerender } = render(
        <>
          <ConfirmModal 
            isOpen={true}
            title="Модал 1"
            message="Сообщение 1"
            onConfirm={vi.fn()}
            onCancel={vi.fn()}
          />
          <ConfirmModal 
            isOpen={true}
            title="Модал 2"
            message="Сообщение 2"
            onConfirm={vi.fn()}
            onCancel={vi.fn()}
          />
        </>
      );
      
      expect(screen.getByText("Модал 1")).toBeInTheDocument();
      expect(screen.getByText("Модал 2")).toBeInTheDocument();
    });
  });
});
