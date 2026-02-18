import { test, expect, request } from "@playwright/test";

function rub(n: number) {
  return new Intl.NumberFormat("ru-RU").format(Math.round(n));
}

test.describe("Коллективный взнос → прогресс в реальном времени", () => {
  test("два пользователя вносят взносы, владелец видит апдейт без перезагрузки", async ({ browser, baseURL }) => {
    const backendURL = "http://localhost:8000";
    const api = await request.newContext();

    const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
    const owner = { email: `owner+e2e+${suffix}@example.com`, password: "Pass1234!", name: "Owner E2E" };
    const friendA = { email: `friendA+e2e+${suffix}@example.com`, password: "Pass1234!", name: "Friend A" };
    const friendB = { email: `friendB+e2e+${suffix}@example.com`, password: "Pass1234!", name: "Friend B" };

    for (const u of [owner, friendA, friendB]) {
      const res = await api.post(`${backendURL}/auth/register`, {
        data: u,
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok()) {
        const bodyText = await res.text();
        throw new Error(`register failed ${res.status()}: ${bodyText}`);
      }
    }
    const login = async (user: typeof owner) => {
      const res = await api.post(`${backendURL}/auth/login`, {
        data: { email: user.email, password: user.password },
        headers: { "Content-Type": "application/json" },
      });
      expect(res.ok()).toBeTruthy();
      const cookies = (await res.headersArray()).filter((h) => h.name.toLowerCase() === "set-cookie");
      const tokenCookie = cookies.map((h) => h.value).find((v) => v && v.includes("access_token=")) || "";
      const token = /access_token=([^;]+)/.exec(tokenCookie)?.[1];
      expect(token).toBeTruthy();
      return token!;
    };
    const ownerToken = await login(owner);
    const friendAToken = await login(friendA);
    const friendBToken = await login(friendB);

    const authed = async (token: string) =>
      await request.newContext({
        baseURL: backendURL,
        extraHTTPHeaders: { Cookie: `access_token=${token}` },
      });

    const ownerApi = await authed(ownerToken);
    const wlRes = await ownerApi.post(`/wishlists`, {
      data: {
        title: "E2E Реальное время",
        description: "Проверка прогресса",
        privacy: "public",
        is_secret_santa: false,
        access_emails: [],
      },
      headers: { "Content-Type": "application/json" },
    });
    expect(wlRes.ok()).toBeTruthy();
    const wishlist = await wlRes.json();
    const slug: string = wishlist.slug;

    const giftRes = await ownerApi.post(`/wishlists/${slug}/gifts`, {
      data: {
        title: "Совместный подарок",
        price: 1000,
        is_collective: true,
        is_private: false,
      },
      headers: { "Content-Type": "application/json" },
    });
    expect(giftRes.ok()).toBeTruthy();
    const gift = await giftRes.json();
    const giftId: number = gift.id;

    const newContext = async (token: string) => {
      const ctx = await browser.newContext({
        baseURL,
      });
      await ctx.addCookies([
        { name: "access_token", value: token, domain: "localhost", path: "/" },
      ]);
      return ctx;
    };

    const ownerCtx = await newContext(ownerToken);
    const ownerPage = await ownerCtx.newPage();
    await ownerPage.goto(`/wishlist/${slug}`);
    await expect(ownerPage.getByText(new RegExp(`Собрано\\s*0\\s*₽\\s*из\\s*${rub(1000)}\\s*₽`))).toBeVisible();

    const friendCtx = await newContext(friendAToken);
    const friendPage = await friendCtx.newPage();
    await friendPage.goto(`/wishlist/${slug}`);
    await friendPage.getByRole("button", { name: "Внести вклад" }).click();
    await friendPage.getByPlaceholder("Сумма вклада").fill("200");
    await friendPage.getByRole("button", { name: "Внести", exact: true }).click();

    await expect(ownerPage.getByText(new RegExp(`Собрано\\s*${rub(200)}\\s*₽\\s*из\\s*${rub(1000)}\\s*₽`))).toBeVisible();

    // Имитация сетевой задержки для ещё одного взноса
    await friendPage.route("**/api/gifts/**/contribute", async (route) => {
      setTimeout(() => route.continue(), 600);
    });
    await friendPage.getByRole("button", { name: "Внести вклад" }).click();
    await friendPage.getByPlaceholder("Сумма вклада").fill("100");
    await friendPage.getByRole("button", { name: "Внести", exact: true }).click();

    // Параллельный взнос второго друга
    const friendCtx2 = await newContext(friendBToken);
    const friendPage2 = await friendCtx2.newPage();
    await friendPage2.goto(`/wishlist/${slug}`);
    await friendPage2.getByRole("button", { name: "Внести вклад" }).click();
    await friendPage2.getByPlaceholder("Сумма вклада").fill("100");
    await Promise.all([
    await friendPage2.getByRole("button", { name: "Внести", exact: true }).click(),
      friendPage.waitForLoadState("networkidle"),
    ]);

    // Ожидаем суммарный прогресс 400 ₽
    await expect(
      ownerPage.getByText(new RegExp(`Собрано\\s*${rub(400)}\\s*₽\\s*из\\s*${rub(1000)}\\s*₽`))
    ).toBeVisible({ timeout: 10_000 });

    await ownerCtx.close();
    await friendCtx.close();
    await friendCtx2.close();
    await api.dispose();
    await ownerApi.dispose();
  });
});
