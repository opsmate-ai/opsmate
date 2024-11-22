package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestOsInventory(t *testing.T) {
	inventory, err := osInventory()
	assert.NoError(t, err)

	t.Logf("inventory: %+v", inventory)

	assert.NotNil(t, inventory)
	assert.NotEmpty(t, inventory["os"])
	assert.NotEmpty(t, inventory["arch"])
	assert.NotEmpty(t, inventory["cpus"])
	assert.NotEmpty(t, inventory["memInGB"])
}
