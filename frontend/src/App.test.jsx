import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

function mockFetch() {
  global.fetch = vi.fn((url) => {
    if (String(url).includes("/v1/tracks")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          items: [
            {
              TrackId: 1,
              TrackName: "Love Song",
              AlbumTitle: "Album 1",
              ArtistName: "Artist 1",
              GenreName: "Rock",
              UnitPrice: 0.99,
            },
          ],
        }),
      });
    }

    if (String(url).includes("/v1/purchases")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          items: [
            {
              InvoiceId: 1,
              TrackId: 1,
              TrackName: "Love Song",
              ArtistName: "Artist 1",
              GenreName: "Rock",
              Quantity: 1,
              LineTotal: 0.99,
            },
          ],
        }),
      });
    }

    if (String(url).includes("/v1/stats/artists")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ items: [] }),
      });
    }

    if (String(url).includes("/v1/stats/genres")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ items: [] }),
      });
    }

    if (String(url).includes("/v1/albums")) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ items: [] }),
      });
    }

    return Promise.resolve({
      ok: true,
      json: async () => ({}),
    });
  });
}

describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    mockFetch();
  });

  it("muestra login si no hay token", () => {
    render(<App />);
    expect(screen.getByText("Login / Register")).toBeInTheDocument();
  });

  it("si el usuario ya compró una canción, aparece Comprada", async () => {
    localStorage.setItem("token", "abc");
    localStorage.setItem("role", "user");
    localStorage.setItem("username", "juan");

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Comprada ✅")).toBeInTheDocument();
    });
  });

  it("admin no ve pestaña Mis compras", async () => {
    localStorage.setItem("token", "abc");
    localStorage.setItem("role", "admin");
    localStorage.setItem("username", "admin");

    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText("Mis compras")).not.toBeInTheDocument();
    });
  });
});
