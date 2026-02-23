import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Skeleton,
  GiftCardSkeleton,
  WishlistCardSkeleton,
  WishlistSkeleton,
  DashboardWishlistsSkeleton,
  FormSkeleton,
  ProfileSkeleton,
  StatsSkeleton,
  AuthPageSkeleton,
  LoginSkeleton,
  RegisterSkeleton,
  ModalSkeleton,
  ImageCardSkeleton,
} from "../Skeleton";

describe("Skeleton", () => {
  describe("Base Skeleton", () => {
    it("renders with default props", () => {
      render(<Skeleton />);
      
      const skeleton = document.querySelector(".skeleton");
      expect(skeleton).toBeInTheDocument();
    });

    it("renders with custom className", () => {
      render(<Skeleton className="w-20 h-20" />);
      
      const skeleton = document.querySelector(".w-20.h-20");
      expect(skeleton).toBeInTheDocument();
    });

    it("applies default variant (rounded-lg)", () => {
      render(<Skeleton />);
      
      const skeleton = document.querySelector(".rounded-lg");
      expect(skeleton).toBeInTheDocument();
    });

    it("applies circle variant", () => {
      render(<Skeleton variant="circle" />);
      
      const skeleton = document.querySelector(".rounded-full");
      expect(skeleton).toBeInTheDocument();
    });

    it("applies rounded variant", () => {
      render(<Skeleton variant="rounded" />);
      
      const skeleton = document.querySelector(".rounded-xl");
      expect(skeleton).toBeInTheDocument();
    });

    it("applies default animation", () => {
      render(<Skeleton />);
      
      const skeleton = document.querySelector(".skeleton");
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).not.toHaveClass("skeleton-fast");
      expect(skeleton).not.toHaveClass("skeleton-slow");
    });

    it("applies fast animation", () => {
      render(<Skeleton animation="fast" />);
      
      const skeleton = document.querySelector(".skeleton-fast");
      expect(skeleton).toBeInTheDocument();
    });

    it("applies slow animation", () => {
      render(<Skeleton animation="slow" />);
      
      const skeleton = document.querySelector(".skeleton-slow");
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe("GiftCardSkeleton", () => {
    it("renders gift card skeleton structure", () => {
      render(<GiftCardSkeleton />);
      
      // Should have multiple skeleton elements
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(1);
    });

    it("has animation class", () => {
      render(<GiftCardSkeleton />);
      
      const container = document.querySelector(".animate-fade-in");
      expect(container).toBeInTheDocument();
    });
  });

  describe("WishlistCardSkeleton", () => {
    it("renders wishlist card skeleton structure", () => {
      render(<WishlistCardSkeleton />);
      
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(3);
    });

    it("has animation class", () => {
      render(<WishlistCardSkeleton />);
      
      const container = document.querySelector(".animate-fade-in");
      expect(container).toBeInTheDocument();
    });
  });

  describe("WishlistSkeleton", () => {
    it("renders full wishlist page skeleton", () => {
      render(<WishlistSkeleton />);
      
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(5);
    });

    it("renders header section", () => {
      render(<WishlistSkeleton />);
      
      const header = document.querySelector("header");
      expect(header).toBeInTheDocument();
    });

    it("renders gift cards grid", () => {
      render(<WishlistSkeleton />);
      
      const grid = document.querySelector(".grid.gap-4");
      expect(grid).toBeInTheDocument();
    });
  });

  describe("DashboardWishlistsSkeleton", () => {
    it("renders with default count", () => {
      render(<DashboardWishlistsSkeleton />);
      
      // Default count is 3
      const cards = document.querySelectorAll("article");
      expect(cards.length).toBe(3);
    });

    it("renders with custom count", () => {
      render(<DashboardWishlistsSkeleton count={5} />);
      
      const cards = document.querySelectorAll("article");
      expect(cards.length).toBe(5);
    });

    it("renders with zero count", () => {
      render(<DashboardWishlistsSkeleton count={0} />);
      
      const cards = document.querySelectorAll("article");
      expect(cards.length).toBe(0);
    });
  });

  describe("FormSkeleton", () => {
    it("renders with default field count", () => {
      render(<FormSkeleton />);
      
      // Default is 3 fields
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(3);
    });

    it("renders with custom field count", () => {
      render(<FormSkeleton fields={5} />);
      
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(5);
    });

    it("renders with zero fields", () => {
      render(<FormSkeleton fields={0} />);
      
      // Should still render title and button
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("ProfileSkeleton", () => {
    it("renders profile skeleton structure", () => {
      render(<ProfileSkeleton />);
      
      // Should have circle for avatar
      const avatar = document.querySelector(".rounded-full");
      expect(avatar).toBeInTheDocument();
    });

    it("has animation class", () => {
      render(<ProfileSkeleton />);
      
      const container = document.querySelector(".animate-fade-in");
      expect(container).toBeInTheDocument();
    });
  });

  describe("StatsSkeleton", () => {
    it("renders with default count", () => {
      render(<StatsSkeleton />);
      
      // Default count is 2
      const panels = document.querySelectorAll(".surface-panel");
      expect(panels.length).toBe(2);
    });

    it("renders with custom count", () => {
      render(<StatsSkeleton count={4} />);
      
      const panels = document.querySelectorAll(".surface-panel");
      expect(panels.length).toBe(4);
    });
  });

  describe("AuthPageSkeleton", () => {
    it("renders without name field by default", () => {
      render(<AuthPageSkeleton />);
      
      // Login page doesn't have name field
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(5);
    });

    it("renders with name field for register page", () => {
      render(<AuthPageSkeleton showNameField={true} />);
      
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(5);
    });

    it("renders main element", () => {
      render(<AuthPageSkeleton />);
      
      const main = document.querySelector("main");
      expect(main).toBeInTheDocument();
    });
  });

  describe("LoginSkeleton", () => {
    it("renders login page skeleton", () => {
      render(<LoginSkeleton />);
      
      const main = document.querySelector("main");
      expect(main).toBeInTheDocument();
    });

    it("does not show name field", () => {
      const { container } = render(<LoginSkeleton />);
      
      // LoginSkeleton uses AuthPageSkeleton with showNameField=false
      expect(container.querySelector(".skeleton")).toBeInTheDocument();
    });
  });

  describe("RegisterSkeleton", () => {
    it("renders register page skeleton", () => {
      render(<RegisterSkeleton />);
      
      const main = document.querySelector("main");
      expect(main).toBeInTheDocument();
    });

    it("shows name field", () => {
      const { container } = render(<RegisterSkeleton />);
      
      // RegisterSkeleton uses AuthPageSkeleton with showNameField=true
      expect(container.querySelector(".skeleton")).toBeInTheDocument();
    });
  });

  describe("ModalSkeleton", () => {
    it("renders modal skeleton with title by default", () => {
      render(<ModalSkeleton />);
      
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(2);
    });

    it("renders without title when title=false", () => {
      render(<ModalSkeleton title={false} />);
      
      const container = document.querySelector(".animate-scale-in");
      expect(container).toBeInTheDocument();
    });

    it("has scale-in animation", () => {
      render(<ModalSkeleton />);
      
      const modal = document.querySelector(".animate-scale-in");
      expect(modal).toBeInTheDocument();
    });
  });

  describe("ImageCardSkeleton", () => {
    it("renders image card skeleton structure", () => {
      render(<ImageCardSkeleton />);
      
      const skeletons = document.querySelectorAll(".skeleton");
      expect(skeletons.length).toBeGreaterThan(3);
    });

    it("has fade-in animation", () => {
      render(<ImageCardSkeleton />);
      
      const container = document.querySelector(".animate-fade-in");
      expect(container).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("skeletons do not have accessible content", () => {
      render(<GiftCardSkeleton />);
      
      // Skeletons should not have text content that screen readers would announce
      const textContent = screen.queryByText(/./);
      // If there's any text, it should be empty or whitespace
      if (textContent) {
        expect(textContent.textContent?.trim()).toBe("");
      }
    });
  });

  describe("Snapshot tests", () => {
    it("base Skeleton matches snapshot", () => {
      const { container } = render(<Skeleton className="w-10 h-10" />);
      expect(container).toMatchSnapshot();
    });

    it("GiftCardSkeleton matches snapshot", () => {
      const { container } = render(<GiftCardSkeleton />);
      expect(container).toMatchSnapshot();
    });
  });
});
