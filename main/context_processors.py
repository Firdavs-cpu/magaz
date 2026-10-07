def cart_count(request):
	cart = request.session.get("cart", {})
	if not isinstance(cart, dict):
		return {"cart_item_count": 0}

	count = 0
	for quantity in cart.values():
		try:
			count += max(0, int(quantity))
		except (TypeError, ValueError):
			continue
	return {"cart_item_count": count}