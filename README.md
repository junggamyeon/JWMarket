# 🛒 JWMarket

**JWMarket** is an advanced, fully-featured **Auction House and Black Market** plugin for Minecraft Bedrock, built on the [Endstone API](https://endstone.dev). It provides a safe, automated, and highly interactive player-driven economy with a seamless user experience.

![Version](https://img.shields.io/badge/version-1.0.2-blue.svg)
![API](https://img.shields.io/badge/API-Endstone-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

---

## 🌟 Key Features

*   **🎨 Native Bedrock GUI:** Forget complex chat commands. JWMarket uses beautiful, native UI forms for browsing, searching, and managing listings.
*   **📦 Auction House (Selling):** List any item in your hand instantly. Full support for custom names, enchantments, and lore.
*   **📈 Buy Orders (Escrow System):** A revolutionary system where players can request items. The money is held in **escrow** and paid out instantly when the order is fulfilled.
*   **🛡️ 100% NBT Preservation:** Every detail—enchantments, custom lore, durability, and item states—is perfectly serialized and restored.
*   **🏠 Offline Delivery & Reclaim:** Sold items or expired listings are managed through a secure "Expired / Reclaim" menu, ensuring no data loss even when players are offline.
*   **🔍 Smart Search & Categories:** Items are automatically grouped into configurable categories (Blocks, Tools, Combat, etc.) with a live search engine.
*   **💰 Dynamic Tax System:** Prevent market spam and control inflation with configurable listing and order taxes.
*   **🌐 Full Localization:** Every string, button, and menu title is 100% configurable in `messages.yml`.

---

## ⚙️ How the Systems Work

### The Auction House (Selling)
1. **List:** A player holds a Sharpness V Diamond Sword and types `/ah sell 5000`.
2. **Store:** The item is removed and serialized into the SQLite database, preserving all NBT data.
3. **Buy:** Player B finds the sword in the "Tools & Weapons" category and clicks **Buy**.
4. **Complete:** Player B pays the 5000 coins (via JWEconomy). Player A receives the funds, and Player B gets the exact Sharpness V sword.

### Buy Orders (Escrow)
1. **Order:** Player A needs 64 Diamonds and creates a Buy Order for 100 coins each.
2. **Escrow:** 6400 coins are immediately deducted from Player A and held in secure escrow.
3. **Fulfill:** Player B sees the order, brings 64 Diamonds, and clicks **Fulfill**.
4. **Swap:** Player B gets the 6400 coins instantly. The Diamonds are moved to Player A's reclaim menu.

---

## 🛠️ Installation & Dependencies

### Dependencies
*   **[JWEconomy](https://github.com/junggamyeon/JWEconomy)** (Required) - Handles all financial transactions.
*   **[endstone-inventoryui](https://github.com/junggamyeon/endstone-inventoryui)** (Recommended) - For enhanced UI interactions.

---

## 📜 Commands & Permissions

| Command | Permission | Description |
|:---|:---|:---|
| `/ah` | `jwmarket.command.ah` | Opens the main Auction House GUI. |
| `/ah sell <price>` | `jwmarket.command.ah` | Lists the held item for the specified price. |
| `/ah search <query>` | `jwmarket.command.ah` | Searches the market for a specific keyword. |
| `/ah expired` | `jwmarket.command.ah` | View and reclaim expired or cancelled items. |
| `/ah reload` | `jwmarket.command.ah.reload` | **(Admin)** Reloads all configuration files. |
| `/orders` | `jwmarket.command.ah` | Opens the Buy Orders / Global Market GUI. |

---

## 📝 Configuration

JWMarket generates three highly customizable files:

### `config.yml`
Adjust tax rates, listing limits, and item blacklists.
```yaml
market:
  listing_tax_percent: 5.0    # Tax charged to list an item.
  max_active_listings: 15     # Max items per player.
  disabled_items:             # Banned items.
    - "minecraft:bedrock"
```

### `categories.yml`
Define how items are grouped in the GUI.
```yaml
blocks:
  display_name: "Blocks"
  icon: "textures/blocks/grass_side_carried"
  items: ["minecraft:dirt", "minecraft:stone"]
```

### `messages.yml`
Translate the entire plugin into any language and customize the color scheme.

---

## 📄 License

This project is licensed under the **MIT License**.
