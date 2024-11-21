package main

import (
	"context"
	"fmt"
	"log"
	"net/url"
	"os"

	opsmatesdk "github.com/jingkaihe/opsmate/cli/sdk"
	"github.com/olekukonko/tablewriter"
	"github.com/urfave/cli/v2"
)

type clientCtxKey struct{}

func main() {

	app := &cli.App{
		Name:  "opsmate",
		Usage: "opsmate is a command line tool for solving production issues",
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:  "endpoint",
				Usage: "endpoint to use",
				Value: "http://127.0.0.1:8000",
			},
		},
		Before: func(c *cli.Context) error {
			client, err := getClient(c.String("endpoint"))
			if err != nil {
				return err
			}
			c.Context = context.WithValue(c.Context, clientCtxKey{}, client)
			return nil
		},
		Commands: []*cli.Command{
			{
				Name:  "list-models",
				Usage: "list available large language models",
				Action: func(c *cli.Context) error {
					client := c.Context.Value(clientCtxKey{}).(*opsmatesdk.APIClient)

					req := client.DefaultAPI.ModelsApiV1ModelsGet(c.Context)

					models, resp, err := req.Execute()
					if err != nil {
						return err
					}
					defer resp.Body.Close()

					table := tablewriter.NewWriter(os.Stdout)
					table.SetHeader([]string{"PROVIDER", "MODEL"})

					for _, model := range models {
						table.Append([]string{
							model.GetProvider(),
							model.GetModel(),
						})
					}

					table.Render()
					return nil
				},
			},
			{
				Name:  "status",
				Usage: "get the status of the server",
				Action: func(c *cli.Context) error {
					client := c.Context.Value(clientCtxKey{}).(*opsmatesdk.APIClient)
					req := client.DefaultAPI.HealthApiV1HealthGet(c.Context)
					health, resp, err := req.Execute()
					if err != nil {
						return err
					}
					defer resp.Body.Close()
					fmt.Println(health.GetStatus())
					return nil
				},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		log.Fatal(err)
	}
}

func getClient(endpoint string) (*opsmatesdk.APIClient, error) {
	cfg := opsmatesdk.NewConfiguration()

	url, err := url.Parse(endpoint)
	if err != nil {
		return nil, err
	}
	cfg.Host = url.Host
	cfg.Scheme = url.Scheme
	client := opsmatesdk.NewAPIClient(cfg)
	return client, nil
}
